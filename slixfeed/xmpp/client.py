#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

FIXME

1) Function check_readiness or event "changed_status" is causing for
   triple status messages and also false ones that indicate of lack
   of feeds.

TODO

1) Use loop (with gather) instead of TaskGroup.

2) Assure message delivery before calling a new task.
    See https://slixmpp.readthedocs.io/en/latest/event_index.html#term-marker_acknowledged

3) XHTTML-IM
    case _ if message_lowercase.startswith("html"):
        message['html']="
Parse me!
"
        self.send_message(
            mto=jid,
            mfrom=self.boundjid.bare,
            mhtml=message
            )

NOTE

1) Self presence
    Apparently, it is possible to view self presence.
    This means that there is no need to store presences in order to switch or restore presence.
    check_readiness
    📂 Send a URL from a blog or a news website.
    JID: self.boundjid.bare
    MUC: self.alias

2) Extracting attribute using xmltodict.
    import xmltodict
    message = xmltodict.parse(str(message))
    jid = message["message"]["x"]["@jid"]

"""

import asyncio
import logging
# import os
from random import randrange
import slixmpp
import slixfeed.task as task
from time import sleep

from slixmpp.plugins.xep_0363.http_upload import FileTooBig, HTTPError, UploadServiceNotFound
# from slixmpp.plugins.xep_0402 import BookmarkStorage, Conference
from slixmpp.plugins.xep_0048.stanza import Bookmarks

# import xmltodict
# import xml.etree.ElementTree as ET
# from lxml import etree

import slixfeed.xmpp.bookmark as bookmark
import slixfeed.xmpp.connect as connect
import slixfeed.xmpp.muc as muc
import slixfeed.xmpp.process as process
import slixfeed.xmpp.profile as profile
import slixfeed.xmpp.roster as roster
# import slixfeed.xmpp.service as service
import slixfeed.xmpp.state as state
import slixfeed.xmpp.status as status
import slixfeed.xmpp.utility as utility

main_task = []
jid_tasker = {}
task_manager = {}
loop = asyncio.get_event_loop()
# asyncio.set_event_loop(loop)

# time_now = datetime.now()
# time_now = time_now.strftime("%H:%M:%S")

# def print_time():
#     # return datetime.now().strftime("%H:%M:%S")
#     now = datetime.now()
#     current_time = now.strftime("%H:%M:%S")
#     return current_time


class Slixfeed(slixmpp.ClientXMPP):
    """
    Slixfeed:
    News bot that sends updates from RSS feeds.
    """
    def __init__(self, jid, password, hostname=None, port=None, alias=None):
        slixmpp.ClientXMPP.__init__(self, jid, password)

        # NOTE
        # The bot works fine when the nickname is hardcoded; or
        # The bot won't join some MUCs when its nickname has brackets
        self.alias = alias
        # The session_start event will be triggered when
        # the bot establishes its connection with the server
        # and the XML streams are ready for use. We want to
        # listen for this event so that we we can initialize
        # our roster.
        self.add_event_handler("session_start",
                               self.on_session_start)
        self.add_event_handler("session_resumed",
                               self.on_session_resumed)
        self.add_event_handler("got_offline", print("got_offline"))
        # self.add_event_handler("got_online", self.check_readiness)
        self.add_event_handler("changed_status",
                               self.on_changed_status)
        self.add_event_handler("presence_available",
                               self.on_presence_available)
        self.add_event_handler("presence_unavailable",
                               self.on_presence_unavailable)
        self.add_event_handler("chatstate_active",
                               self.on_chatstate_active)
        self.add_event_handler("chatstate_composing",
                               self.on_chatstate_composing)
        self.add_event_handler("chatstate_gone",
                               self.on_chatstate_gone)
        self.add_event_handler("chatstate_inactive",
                               self.on_chatstate_inactive)
        self.add_event_handler("chatstate_paused",
                               self.on_chatstate_paused)

        # The message event is triggered whenever a message
        # stanza is received. Be aware that that includes
        # MUC messages and error messages.
        self.add_event_handler("message",
                               self.on_message)

        self.add_event_handler("groupchat_invite",
                               self.on_groupchat_invite) # XEP_0045
        self.add_event_handler("groupchat_direct_invite",
                               self.on_groupchat_direct_invite) # XEP_0249
        # self.add_event_handler("groupchat_message", self.message)

        # self.add_event_handler("disconnected", self.reconnect)
        # self.add_event_handler("disconnected", self.inspect_connection)

        self.add_event_handler("reactions",
                               self.on_reactions)
        self.add_event_handler("presence_error",
                               self.on_presence_error)
        self.add_event_handler("presence_subscribe",
                               self.on_presence_subscribe)
        self.add_event_handler("presence_subscribed",
                               self.on_presence_subscribed)
        self.add_event_handler("presence_unsubscribed",
                               self.on_presence_unsubscribed)

        # Initialize event loop
        # self.loop = asyncio.get_event_loop()

        # handlers for connection events
        self.connection_attempts = 0
        self.max_connection_attempts = 10
        self.add_event_handler("connection_failed", self.on_connection_failed)
        self.add_event_handler("session_end", self.on_session_end)


    # TODO Test
    async def on_groupchat_invite(self, message):
        logging.warning("on_groupchat_invite")
        inviter = message["from"].bare
        muc_jid = message['groupchat_invite']['jid']
        await muc.join(self, inviter, muc_jid)
        await bookmark.add(self, muc_jid)


    # NOTE Tested with Gajim and Psi
    async def on_groupchat_direct_invite(self, message):
        inviter = message["from"].bare
        muc_jid = message['groupchat_invite']['jid']
        await muc.join(self, inviter, muc_jid)
        await bookmark.add(self, muc_jid)


    async def on_session_end(self, event):
        message = "Session has ended."
        await connect.recover_connection(self, message)


    async def on_connection_failed(self, event):
        message = "Connection has failed.  Reason: {}".format(event)
        await connect.recover_connection(self, message)


    async def on_session_start(self, event):
        await process.event(self)
        await muc.autojoin(self)
        profile.set_identity(self, "client")
        await profile.update(self)
        task.ping_task(self)
        
        # await Service.capabilities(self)
        # Service.commands(self)
        # Service.reactions(self)
        
        self.service_commands()
        self.service_reactions()


    async def on_session_resumed(self, event):
        await process.event(self)
        await muc.autojoin(self)
        profile.set_identity(self, "client")
        
        # await Service.capabilities(self)
        # Service.commands(self)
        # Service.reactions(self)
        
        self.service_commands()
        self.service_reactions()


    # TODO Request for subscription
    async def on_message(self, message):
        jid = message["from"].bare
        if "chat" == await utility.get_chat_type(self, jid):
            await roster.add(self, jid)
            await state.request(self, jid)
        await process.message(self, message)
        # chat_type = message["type"]
        # message_body = message["body"]
        # message_reply = message.reply


    async def on_changed_status(self, presence):
        # await task.check_readiness(self, presence)
        jid = presence['from'].bare
        if presence['show'] in ('away', 'dnd', 'xa'):
            await task.clean_tasks_xmpp(jid, ['interval'])
            await task.start_tasks_xmpp(self, jid, ['status', 'check'])


    async def on_presence_subscribe(self, presence):
        jid = presence["from"].bare
        await state.request(self, jid)


    async def on_presence_subscribed(self, presence):
        jid = presence["from"].bare
        process.greet(self, jid)


    async def on_presence_available(self, presence):
        # TODO Add function to check whether task is already running or not
        # await task.start_tasks(self, presence)
        # NOTE Already done inside the start-task function
        jid = presence["from"].bare
        await task.start_tasks_xmpp(self, jid)


    async def on_presence_unsubscribed(self, presence):
        await state.unsubscribed(self, presence)
        jid = presence["from"].bare
        await roster.remove(self, jid)


    async def on_presence_unavailable(self, presence):
        jid = presence["from"].bare
        # await task.stop_tasks(self, jid)
        await task.clean_tasks_xmpp(jid)


    # TODO
    # Send message that database will be deleted within 30 days
    # Check whether JID is in bookmarks or roster
    # If roster, remove contact JID into file 
    # If bookmarks, remove groupchat JID into file 
    async def on_presence_error(self, presence):
        print("on_presence_error")
        print(presence)
        jid = presence["from"].bare
        await task.clean_tasks_xmpp(jid)


    async def on_reactions(self, message):
        print(message['from'])
        print(message['reactions']['values'])


    async def on_chatstate_active(self, message):
        if message['type'] in ('chat', 'normal'):
            jid = message['from'].bare
            # await task.clean_tasks_xmpp(jid, ['status'])
            await task.start_tasks_xmpp(self, jid, ['status'])


    async def on_chatstate_composing(self, message):
        if message['type'] in ('chat', 'normal'):
            jid = message['from'].bare
            # await task.clean_tasks_xmpp(jid, ['status'])
            status_text='Press "help" for manual, or "info" for information.'
            status.send(self, jid, status_text)


    async def on_chatstate_gone(self, message):
        if message['type'] in ('chat', 'normal'):
            jid = message['from'].bare
            # await task.clean_tasks_xmpp(jid, ['status'])
            await task.start_tasks_xmpp(self, jid, ['status'])


    async def on_chatstate_inactive(self, message):
        if message['type'] in ('chat', 'normal'):
            jid = message['from'].bare
            # await task.clean_tasks_xmpp(jid, ['status'])
            await task.start_tasks_xmpp(self, jid, ['status'])


    async def on_chatstate_paused(self, message):
        if message['type'] in ('chat', 'normal'):
            jid = message['from'].bare
            # await task.clean_tasks_xmpp(jid, ['status'])
            await task.start_tasks_xmpp(self, jid, ['status'])
