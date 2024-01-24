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

import slixfeed.xmpp.connect as connect
import slixfeed.xmpp.muc as muc
import slixfeed.xmpp.process as process
import slixfeed.xmpp.profile as profile
import slixfeed.xmpp.roster as roster
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


class Slixfeed(slixmpp.ComponentXMPP):
    """
    Slixmpp
    -------
    News bot that sends updates from RSS feeds.
    """
    def __init__(self, jid, secret, hostname, port, alias):
        slixmpp.ComponentXMPP.__init__(self, jid, secret, hostname, port)

        # The session_start event will be triggered when
        # the bot establishes its connection with the server
        # and the XML streams are ready for use. We want to
        # listen for this event so that we we can initialize
        # our roster.
        self.add_event_handler("session_start", self.on_session_start)
        self.add_event_handler("session_resumed", self.on_session_resumed)
        self.add_event_handler("got_offline", print("got_offline"))
        # self.add_event_handler("got_online", self.check_readiness)
        self.add_event_handler("changed_status", self.on_changed_status)
        self.add_event_handler("presence_available", self.on_presence_available)
        self.add_event_handler("presence_unavailable", self.on_presence_unavailable)

        self.add_event_handler("changed_subscription", self.on_changed_subscription)

        self.add_event_handler("chatstate_active", self.on_chatstate_active)
        self.add_event_handler("chatstate_gone", self.on_chatstate_gone)
        self.add_event_handler("chatstate_composing", self.check_chatstate_composing)
        self.add_event_handler("chatstate_paused", self.check_chatstate_paused)

        # The message event is triggered whenever a message
        # stanza is received. Be aware that that includes
        # MUC messages and error messages.
        self.add_event_handler("message", self.on_message)

        self.add_event_handler("groupchat_invite", self.on_groupchat_invite) # XEP_0045
        self.add_event_handler("groupchat_direct_invite", self.on_groupchat_direct_invite) # XEP_0249
        # self.add_event_handler("groupchat_message", self.message)

        # self.add_event_handler("disconnected", self.reconnect)
        # self.add_event_handler("disconnected", self.inspect_connection)

        self.add_event_handler("reactions", self.on_reactions)
        self.add_event_handler("presence_error", self.on_presence_error)
        self.add_event_handler("presence_subscribe", self.on_presence_subscribe)
        self.add_event_handler("presence_subscribed", self.on_presence_subscribed)
        self.add_event_handler("presence_unsubscribe", self.on_presence_unsubscribe)
        self.add_event_handler("presence_unsubscribed", self.on_presence_unsubscribed)

        # Initialize event loop
        # self.loop = asyncio.get_event_loop()

        # handlers for connection events
        self.connection_attempts = 0
        self.max_connection_attempts = 10
        self.add_event_handler("connection_failed", self.on_connection_failed)
        self.add_event_handler("session_end", self.on_session_end)


    async def on_groupchat_invite(self, message):
        print("on_groupchat_invite")
        await muc.accept_invitation(self, message)


    async def on_groupchat_direct_invite(self, message):
        print("on_groupchat_direct_invite")
        await muc.accept_invitation(self, message)


    async def on_session_end(self, event):
        message = "Session has ended. Reason: {}".format(event)
        await connect.recover_connection(self, event, message)


    async def on_connection_failed(self, event):
        message = "Connection has failed. Reason: {}".format(event)
        await connect.recover_connection(self, event, message)


    async def on_session_start(self, event):
        await process.event_component(self, event)
        # await muc.autojoin(self)
        await profile.update(self)


    async def on_session_resumed(self, event):
        await process.event_component(self, event)
        # await muc.autojoin(self)


    # TODO Request for subscription
    async def on_message(self, message):
        # print(message)
        # breakpoint()
        jid = message["from"].bare
        # if "chat" == await utility.jid_type(self, jid):
        #     await roster.add(self, jid)
        #     await state.request(self, jid)
        # chat_type = message["type"]
        # message_body = message["body"]
        # message_reply = message.reply
        await process.message(self, message)


    async def on_changed_status(self, presence):
        await task.check_readiness(self, presence)


    # TODO Request for subscription
    async def on_presence_subscribe(self, presence):
        print("on_presence_subscribe")
        print(presence)
        jid = presence["from"].bare
        # await state.request(self, jid)
        self.send_presence_subscription(
            pto=jid,
            pfrom=self.boundjid.bare,
            ptype="subscribe",
            pnick=self.alias
            )


    async def on_presence_subscribed(self, presence):
        jid = presence["from"].bare
        process.greet(self, jid)


    async def on_presence_available(self, presence):
        # TODO Add function to check whether task is already running or not
        await task.start_tasks(self, presence)


    async def on_presence_unsubscribed(self, presence):
        await state.unsubscribed(self, presence)


    async def on_presence_unavailable(self, presence):
        await task.stop_tasks(self, presence)


    async def on_changed_subscription(self, presence):
        print("on_changed_subscription")
        print(presence)
        jid = presence["from"].bare
        # breakpoint()


    async def on_presence_unsubscribe(self, presence):
        print("on_presence_unsubscribe")
        print(presence)


    async def on_presence_error(self, presence):
        print("on_presence_error")
        print(presence)


    async def on_reactions(self, message):
        print("on_reactions")
        print(message)


    async def on_chatstate_active(self, message):
        print("on_chatstate_active")
        print(message)


    async def on_chatstate_gone(self, message):
        print("on_chatstate_gone")
        print(message)


    async def check_chatstate_composing(self, message):
        print("def check_chatstate_composing")
        print(message)
        if message["type"] in ("chat", "normal"):
            jid = message["from"].bare
        status_text="Press \"help\" for manual."
        self.send_presence(
            # pshow=status_mode,
            pstatus=status_text,
            pto=jid,
            )


    async def check_chatstate_paused(self, message):
        print("def check_chatstate_paused")
        print(message)
        if message["type"] in ("chat", "normal"):
            jid = message["from"].bare
        await task.refresh_task(
            self,
            jid,
            task.send_status,
            "status",
            20
            )

