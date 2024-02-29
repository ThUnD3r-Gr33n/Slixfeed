#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

TODO

1) Look into self.set_jid in order to be able to join to groupchats
   https://slixmpp.readthedocs.io/en/latest/api/basexmpp.html#slixmpp.basexmpp.BaseXMPP.set_jid

2) czar
   https://slixmpp.readthedocs.io/en/latest/api/plugins/xep_0223.html
   https://slixmpp.readthedocs.io/en/latest/api/plugins/xep_0222.html#module-slixmpp.plugins.xep_0222

"""

import asyncio
import logging
# import os
# from random import randrange
import slixmpp
import slixfeed.task as task
# from time import sleep

# from slixmpp.plugins.xep_0363.http_upload import FileTooBig, HTTPError, UploadServiceNotFound
# from slixmpp.plugins.xep_0402 import BookmarkStorage, Conference
# from slixmpp.plugins.xep_0048.stanza import Bookmarks

# import xmltodict
# import xml.etree.ElementTree as ET
# from lxml import etree

import slixfeed.config as config
from slixfeed.version import __version__
from slixfeed.xmpp.connect import XmppConnect
# NOTE MUC is possible for component
# from slixfeed.xmpp.muc import XmppGroupchat
from slixfeed.xmpp.message import XmppMessage
import slixfeed.xmpp.process as process
import slixfeed.xmpp.profile as profile
# from slixfeed.xmpp.roster import XmppRoster
# import slixfeed.xmpp.service as service
from slixfeed.xmpp.presence import XmppPresence
# from slixmpp.xmlstream import ET
# from slixmpp.xmlstream.handler import Callback
# from slixmpp.xmlstream.matcher import MatchXPath

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


class SlixfeedComponent(slixmpp.ComponentXMPP):
    """
    Slixfeed:
    News bot that sends updates from RSS feeds.
    """
    def __init__(self, jid, secret, hostname, port, alias=None):
        slixmpp.ComponentXMPP.__init__(self, jid, secret, hostname, port)

        # NOTE
        # The bot works fine when the nickname is hardcoded; or
        # The bot won't join some MUCs when its nickname has brackets

        # Handler for nickname
        self.alias = alias

        # Handlers for tasks
        self.task_manager = {}

        # Handlers for ping
        self.task_ping_instance = {}

        # Handlers for connection events
        self.connection_attempts = 0
        self.max_connection_attempts = 10

        self.add_event_handler("session_start",
                               self.on_session_start)
        self.add_event_handler("session_resumed",
                               self.on_session_resumed)
        self.add_event_handler("got_offline", print("got_offline"))
        # self.add_event_handler("got_online", self.check_readiness)
        self.add_event_handler("changed_status",
                               self.on_changed_status)
        self.add_event_handler("disco_info",
                               self.on_disco_info)
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

        # self.add_event_handler("groupchat_invite",
        #                        self.on_groupchat_invite) # XEP_0045
        # self.add_event_handler("groupchat_direct_invite",
        #                        self.on_groupchat_direct_invite) # XEP_0249
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

        self.add_event_handler('connection_failed',
                               self.on_connection_failed)
        self.add_event_handler('session_end',
                               self.on_session_end)


    # async def on_groupchat_invite(self, message):
    #     logging.warning("on_groupchat_invite")
    #     inviter = message['from'].bare
    #     muc_jid = message['groupchat_invite']['jid']
    #     await muc.join(self, inviter, muc_jid)
    #     await bookmark.add(self, muc_jid)


    # NOTE Tested with Gajim and Psi
    # async def on_groupchat_direct_invite(self, message):
    #     inviter = message['from'].bare
    #     muc_jid = message['groupchat_invite']['jid']
    #     await muc.join(self, inviter, muc_jid)
    #     await bookmark.add(self, muc_jid)


    async def on_session_end(self, event):
        message = 'Session has ended.'
        XmppConnect.recover(self, message)


    async def on_connection_failed(self, event):
        message = 'Connection has failed.  Reason: {}'.format(event)
        XmppConnect.recover(self, message)


    async def on_session_start(self, event):
        # self.send_presence()
        profile.set_identity(self, 'service')
        self.service_commands()
        self.service_reactions()
        await self['xep_0115'].update_caps()
        # await XmppGroupchat.autojoin(self)
        await profile.update(self)
        task.task_ping(self)
        # bookmarks = await self.plugin['xep_0048'].get_bookmarks()
        # XmppGroupchat.autojoin(self, bookmarks)
        if config.get_value('accounts', 'XMPP', 'operator'):
            jid_op = config.get_value('accounts', 'XMPP', 'operator')
            message_body = 'Slixfeed version {}'.format(__version__)
            XmppMessage.send(self, jid_op, message_body, 'chat')


    def on_session_resumed(self, event):
        # self.send_presence()
        profile.set_identity(self, 'service')
        self['xep_0115'].update_caps()
        # await XmppGroupchat.autojoin(self)


    async def on_disco_info(self, DiscoInfo):
        jid = DiscoInfo['from']
        # self.service_commands()
        # self.service_reactions()
        # self.send_presence(pto=jid)
        await self['xep_0115'].update_caps(jid=jid)


    async def on_message(self, message):
        jid = message['from'].bare
        if jid == self.boundjid.bare:
            status_type = 'dnd'
            status_message = ('Slixfeed is not designed to receive messages '
                              'from itself')
            XmppPresence.send(self, jid, status_message,
                              status_type=status_type)
            await asyncio.sleep(5)
            status_message = ('Slixfeed news bot from RSS Task Force')
            XmppPresence.send(self, jid, status_message)
        else:
            # TODO Request for subscription
            # if "chat" == await XmppUtility.get_chat_type(self, jid):
            #     presence_probe = ET.Element('presence')
            #     presence_probe.attrib['type'] = 'probe'
            #     presence_probe.attrib['to'] = jid
            #     print('presence_probe')
            #     print(presence_probe)
            #     self.send_raw(str(presence_probe))
            #     presence_probe.send()

            await process.message(self, message)
        # chat_type = message["type"]
        # message_body = message["body"]
        # message_reply = message.reply


    async def on_changed_status(self, presence):
        # await task.check_readiness(self, presence)
        jid = presence['from'].bare
        if jid in self.boundjid.bare:
            return
        if presence['show'] in ('away', 'dnd', 'xa'):
            task.clean_tasks_xmpp(self, jid, ['interval'])
            await task.start_tasks_xmpp(self, jid, ['status', 'check'])


    async def on_presence_subscribe(self, presence):
        jid = presence['from'].bare
        if not self.client_roster[jid]['to']:
        # XmppPresence.subscription(self, jid, 'subscribe')
            XmppPresence.subscription(self, jid, 'subscribed')
            await XmppRoster.add(self, jid)
            status_message = '✒️ Share online status to receive updates'
            XmppPresence.send(self, jid, status_message)
            message_subject = 'RSS News Bot'
            message_body = 'Share online status to receive updates.'
            XmppMessage.send_headline(self, jid, message_subject, message_body,
                                      'chat')


    def on_presence_subscribed(self, presence):
        jid = presence['from'].bare
        # XmppPresence.subscription(self, jid, 'subscribed')
        message_subject = 'RSS News Bot'
        message_body = ('Greetings! I am {}, the news anchor.\n'
                        'My job is to bring you the latest '
                        'news from sources you provide me with.\n'
                        'You may always reach me via xmpp:{}?message'
                        .format(self.alias, self.boundjid.bare))
        XmppMessage.send_headline(self, jid, message_subject, message_body,
                                  'chat')


    async def on_presence_available(self, presence):
        # TODO Add function to check whether task is already running or not
        # await task.start_tasks(self, presence)
        # NOTE Already done inside the start-task function
        jid = presence['from'].bare
        if jid in self.boundjid.bare:
            return
        logging.info('JID {} is available'.format(jid))
        # FIXME TODO Find out what is the source responsible for a couple presences with empty message
        # NOTE This is a temporary solution
        await asyncio.sleep(10)
        await task.start_tasks_xmpp(self, jid)
        self.add_event_handler("presence_unavailable",
                               self.on_presence_unavailable)


    def on_presence_unsubscribed(self, presence):
        jid = presence['from'].bare
        message_body = 'You have been unsubscribed.'
        # status_message = '🖋️ Subscribe to receive updates'
        # status_message = None
        XmppMessage.send(self, jid, message_body, 'chat')
        XmppPresence.subscription(self, jid, 'unsubscribed')
        # XmppPresence.send(self, jid, status_message,
        #                   presence_type='unsubscribed')
        # XmppRoster.remove(self, jid)


    def on_presence_unavailable(self, presence):
        jid = presence['from'].bare
        logging.info('JID {} is unavailable'.format(jid))
        # await task.stop_tasks(self, jid)
        task.clean_tasks_xmpp(self, jid)

        # NOTE Albeit nice to ~have~ see, this would constantly
        #      send presence messages to server to no end.
        status_message = 'Farewell'
        XmppPresence.send(self, jid, status_message,
                          presence_type='unavailable')
        self.del_event_handler("presence_unavailable",
                               self.on_presence_unavailable)


    # TODO
    # Send message that database will be deleted within 30 days
    # Check whether JID is in bookmarks or roster
    # If roster, remove contact JID into file 
    # If bookmarks, remove groupchat JID into file 
    def on_presence_error(self, presence):
        jid = presence["from"].bare
        logging.info('JID {} (error)'.format(jid))
        task.clean_tasks_xmpp(self, jid)


    def on_reactions(self, message):
        print(message['from'])
        print(message['reactions']['values'])


    async def on_chatstate_active(self, message):
        jid = message['from'].bare
        if jid in self.boundjid.bare:
            return
        if message['type'] in ('chat', 'normal'):
            # NOTE: Required for Cheogram
            # await self['xep_0115'].update_caps(jid=jid)
            # self.send_presence(pto=jid)
            # task.clean_tasks_xmpp(self, jid, ['status'])
            await asyncio.sleep(5)
            await task.start_tasks_xmpp(self, jid, ['status'])


    async def on_chatstate_composing(self, message):
        if message['type'] in ('chat', 'normal'):
            jid = message['from'].bare
            # NOTE: Required for Cheogram
            # await self['xep_0115'].update_caps(jid=jid)
            # self.send_presence(pto=jid)
            # task.clean_tasks_xmpp(self, jid, ['status'])
            await asyncio.sleep(5)
            status_message = ('💡 Send "help" for manual, or "info" for '
                              'information.')
            XmppPresence.send(self, jid, status_message)


    async def on_chatstate_gone(self, message):
        jid = message['from'].bare
        if jid in self.boundjid.bare:
            return
        if message['type'] in ('chat', 'normal'):
            # task.clean_tasks_xmpp(self, jid, ['status'])
            await task.start_tasks_xmpp(self, jid, ['status'])


    async def on_chatstate_inactive(self, message):
        jid = message['from'].bare
        if jid in self.boundjid.bare:
            return
        if message['type'] in ('chat', 'normal'):
            # task.clean_tasks_xmpp(self, jid, ['status'])
            await task.start_tasks_xmpp(self, jid, ['status'])


    async def on_chatstate_paused(self, message):
        jid = message['from'].bare
        if jid in self.boundjid.bare:
            return
        if message['type'] in ('chat', 'normal'):
            # task.clean_tasks_xmpp(self, jid, ['status'])
            await task.start_tasks_xmpp(self, jid, ['status'])



    # NOTE Failed attempt
    # Need to use Super or Inheritance or both
    #     self['xep_0050'].add_command(node='settings',
    #                                  name='Settings',
    #                                  handler=self._handle_settings)
    #     self['xep_0050'].add_command(node='subscriptions',
    #                                  name='Subscriptions',
    #                                  handler=self._handle_subscriptions)


    # async def _handle_settings(self, iq, session):
    #     await XmppCommand._handle_settings(self, iq, session)


    # async def _handle_subscriptions(self, iq, session):
    #     await XmppCommand._handle_subscriptions(self, iq, session)


# TODO Move class Service to a separate file
# class Service(Slixfeed):
#     def __init__(self):
#         super().__init__()

# TODO https://xmpp.org/extensions/xep-0115.html
# https://xmpp.org/extensions/xep-0444.html#disco


    # TODO https://xmpp.org/extensions/xep-0444.html#disco-restricted
    def service_reactions(self):
        """
        Publish allow list of reactions.
    
        Parameters
        ----------
        None.
    
        Returns
        -------
        None.
    
        """
        form = self['xep_0004'].make_form(
            'form', 'Reactions Information'
            )
