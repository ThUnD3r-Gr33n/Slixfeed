#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

TODO

1) Assure message delivery before calling a new task.
    See https://slixmpp.readthedocs.io/en/latest/event_index.html#term-marker_acknowledged

2) XHTTML-IM
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

1) Extracting attribute using xmltodict.
    import xmltodict
    message = xmltodict.parse(str(message))
    jid = message["message"]["x"]["@jid"]

"""


import asyncio
from datetime import datetime
import os
from feedparser import parse
import slixmpp
# from slixmpp.plugins.xep_0363.http_upload import FileTooBig, HTTPError, UploadServiceNotFound
# from slixmpp.plugins.xep_0402 import BookmarkStorage, Conference
# from slixmpp.plugins.xep_0048.stanza import Bookmarks

# import xmltodict
# import xml.etree.ElementTree as ET
# from lxml import etree

import slixfeed.config as config
from slixfeed.config import Config
import slixfeed.crawl as crawl
import slixfeed.dt as dt
import slixfeed.fetch as fetch
from slixfeed.log import Logger
import slixfeed.sqlite as sqlite
from slixfeed.syndication import Feed, FeedTask, Opml
import slixfeed.url as uri
from slixfeed.utilities import Html, Task, Utilities
from slixfeed.version import __version__
from slixfeed.xmpp.bookmark import XmppBookmark
from slixfeed.xmpp.chat import XmppChat, XmppChatTask
from slixfeed.xmpp.connect import XmppConnect, XmppConnectTask
from slixfeed.xmpp.ipc import XmppIpcServer
from slixfeed.xmpp.iq import XmppIQ
from slixfeed.xmpp.message import XmppMessage
from slixfeed.xmpp.muc import XmppMuc
from slixfeed.xmpp.groupchat import XmppGroupchat
from slixfeed.xmpp.presence import XmppPresence
from slixfeed.xmpp.privilege import is_operator, is_access
import slixfeed.xmpp.profile as profile
from slixfeed.xmpp.publish import XmppPubsub, XmppPubsubAction, XmppPubsubTask
from slixfeed.xmpp.roster import XmppRoster
# import slixfeed.xmpp.service as service
from slixfeed.xmpp.status import XmppStatusTask
from slixfeed.xmpp.upload import XmppUpload
from slixfeed.xmpp.utilities import XmppUtilities
import sys
import time

try:
    import tomllib
except:
    import tomli as tomllib

# time_now = datetime.now()
# time_now = time_now.strftime("%H:%M:%S")

# def print_time():
#     # return datetime.now().strftime("%H:%M:%S")
#     now = datetime.now()
#     current_time = now.strftime("%H:%M:%S")
#     return current_time

logger = Logger(__name__)

class XmppClient(slixmpp.ClientXMPP):
    """
    Slixfeed:
    News bot that sends updates from RSS feeds.
    """
    def __init__(self, jid, password, hostname=None, port=None, alias=None):
        slixmpp.ClientXMPP.__init__(self, jid, password)

        # NOTE
        # The bot works fine when the nickname is hardcoded; or
        # The bot won't join some MUCs when its nickname has brackets

        # Handler for nickname
        self.alias = alias

        # Handler for tasks
        self.task_manager = {}

        # Handler for task messages
        self.pending_tasks = {}

        # Handler for task messages counter
        # self.pending_tasks_counter = 0

        # Handler for ping
        self.task_ping_instance = {}

        # Handler for configuration
        self.settings = config.get_values('settings.toml')
        # Handler for operators
        self.operators = config.get_values('accounts.toml', 'xmpp')['operators']

        # self.settings = {}
        # # Populate dict handler
        # Config.add_settings_default(self.settings)

        # Handlers for connection events
        self.connection_attempts = 0
        self.max_connection_attempts = 10
        self.reconnect_timeout = config.get_values('accounts.toml', 'xmpp')['settings']['reconnect_timeout']

        self.register_plugin('xep_0004') # Data Forms
        self.register_plugin('xep_0030') # Service Discovery
        self.register_plugin('xep_0045') # Multi-User Chat
        self.register_plugin('xep_0048') # Bookmarks
        self.register_plugin('xep_0050') # Ad-Hoc Commands
        self.register_plugin('xep_0054') # vcard-temp
        self.register_plugin('xep_0060') # Publish-Subscribe
        # self.register_plugin('xep_0065') # SOCKS5 Bytestreams
        self.register_plugin('xep_0066') # Out of Band Data
        self.register_plugin('xep_0071') # XHTML-IM
        self.register_plugin('xep_0084') # User Avatar
        self.register_plugin('xep_0085') # Chat State Notifications
        self.register_plugin('xep_0115') # Entity Capabilities
        self.register_plugin('xep_0122') # Data Forms Validation
        self.register_plugin('xep_0153') # vCard-Based Avatars
        self.register_plugin('xep_0199', {'keepalive': True}) # XMPP Ping
        self.register_plugin('xep_0203') # Delayed Delivery
        self.register_plugin('xep_0249') # Direct MUC Invitations
        self.register_plugin('xep_0363') # HTTP File Upload
        self.register_plugin('xep_0402') # PEP Native Bookmarks
        self.register_plugin('xep_0444') # Message Reactions

        # proxy_enabled = config.get_value('accounts', 'XMPP', 'proxy_enabled')
        # if proxy_enabled == '1':
        #     values = config.get_value('accounts', 'XMPP', [
        #         'proxy_host',
        #         'proxy_port',
        #         'proxy_username',
        #         'proxy_password'
        #         ])
        #     print('Proxy is enabled: {}:{}'.format(values[0], values[1]))
        #     self.use_proxy = True
        #     self.proxy_config = {
        #         'host': values[0],
        #         'port': values[1],
        #         'username': values[2],
        #         'password': values[3]
        #     }
        #     proxy = {'socks5': (values[0], values[1])}
        #     self.proxy = {'socks5': ('localhost', 9050)}

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
        # self.add_event_handler("presence_unavailable",
        #                        self.on_presence_unavailable)
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
        self.add_event_handler('connection_failed',
                               self.on_connection_failed)
        self.add_event_handler('session_end',
                               self.on_session_end)

        # Connect to the XMPP server and start processing XMPP stanzas.
        self.connect((hostname, port)) if hostname and port else self.connect()
        self.process()


    # TODO Test
    async def on_groupchat_invite(self, message):
        time_begin = time.time()
        jid_full = str(message['from'])
        function_name = sys._getframe().f_code.co_name
        message_log = '{}: jid_full: {}'
        logger.debug(message_log.format(function_name, jid_full))
        muc_jid = message['groupchat_invite']['jid']
        result = await XmppMuc.join(self, muc_jid)
        if result == 'ban':
            message_body = '{} is banned from {}'.format(self.alias, muc_jid)
            jid_bare = message['from'].bare
            # This might not be necessary because JID might not be of the inviter, but rather of the MUC
            XmppMessage.send(self, jid_bare, message_body, 'chat')
            logger.warning(message_body)
            print("on_groupchat_invite")
            print("on_groupchat_invite")
            print("on_groupchat_invite")
            print(jid_full)
            print(jid_full)
            print(jid_full)
            print("on_groupchat_invite")
            print("on_groupchat_invite")
            print("on_groupchat_invite")
        else:
            await XmppBookmark.add(self, muc_jid)
            message_body = ('Greetings! I am {}, the news anchor.\n'
                            'My job is to bring you the latest '
                            'news from sources you provide me with.\n'
                            'You may always reach me via xmpp:{}?message'
                            .format(self.alias, self.boundjid.bare))
            XmppMessage.send(self, muc_jid, message_body, 'groupchat')
        time_end = time.time()
        difference = time_end - time_begin
        if difference > 1: logger.warning('{} (time: {})'.format(function_name,
                                                                 difference))


    # NOTE Tested with Gajim and Psi
    async def on_groupchat_direct_invite(self, message):
        time_begin = time.time()
        jid_full = str(message['from'])
        function_name = sys._getframe().f_code.co_name
        message_log = '{}: jid_full: {}'
        logger.debug(message_log.format(function_name, jid_full))
        muc_jid = message['groupchat_invite']['jid']
        result = await XmppMuc.join(self, muc_jid)
        if result == 'ban':
            message_body = '{} is banned from {}'.format(self.alias, muc_jid)
            jid_bare = message['from'].bare
            XmppMessage.send(self, jid_bare, message_body, 'chat')
            logger.warning(message_body)
        else:
            await XmppBookmark.add(self, muc_jid)
            message_body = ('Greetings! I am {}, the news anchor.\n'
                            'My job is to bring you the latest '
                            'news from sources you provide me with.\n'
                            'You may always reach me via xmpp:{}?message'
                            .format(self.alias, self.boundjid.bare))
            XmppMessage.send(self, muc_jid, message_body, 'groupchat')
        time_end = time.time()
        difference = time_end - time_begin
        if difference > 1: logger.warning('{} (time: {})'.format(function_name,
                                                                 difference))


    async def on_session_end(self, event):
        message = 'Session has ended.'
        XmppConnect.recover(self, message)


    async def on_connection_failed(self, event):
        time_begin = time.time()
        function_name = sys._getframe().f_code.co_name
        message_log = '{}'
        logger.debug(message_log.format(function_name))
        message = 'Connection has failed.  Reason: {}'.format(event)
        XmppConnect.recover(self, message)
        time_end = time.time()
        difference = time_end - time_begin
        if difference > 1: logger.warning('{} (time: {})'.format(function_name,
                                                                 difference))


    async def on_session_start(self, event):
        time_begin = time.time()
        function_name = sys._getframe().f_code.co_name
        message_log = '{}'
        logger.debug(message_log.format(function_name))
        status_message = 'Slixfeed version {}'.format(__version__)
        self.adhoc_commands()
        for operator in self.operators:
            XmppPresence.send(self, operator['jid'], status_message)
        await profile.update(self)
        profile.set_identity(self, 'client')
        await self['xep_0115'].update_caps()
        # self.send_presence()
        await self.get_roster()
        # self.service_reactions()
        XmppConnectTask.ping(self)
        # results = await XmppPubsub.get_pubsub_services(self)
        # for result in results + [{'jid' : self.boundjid.bare,
        #                             'name' : self.alias}]:
        #     jid_bare = result['jid']
        #     if jid_bare not in self.settings:
        #         db_file = config.get_pathname_to_database(jid_bare)
        #         Config.add_settings_jid(self.settings, jid_bare, db_file)
        #     await FeedTask.check_updates(self, jid_bare)
        #     XmppPubsubTask.task_publish(self, jid_bare)
        bookmarks = await XmppBookmark.get_bookmarks(self)
        await XmppGroupchat.autojoin(self, bookmarks)
        if 'ipc' in self.settings and self.settings['ipc']['bsd']:
            # Start Inter-Process Communication
            print('POSIX sockets: Initiating IPC server...')
            self.ipc = asyncio.create_task(XmppIpcServer.ipc(self))
        time_end = time.time()
        difference = time_end - time_begin
        if difference > 1: logger.warning('{} (time: {})'.format(function_name,
                                                                 difference))


    async def on_session_resumed(self, event):
        time_begin = time.time()
        function_name = sys._getframe().f_code.co_name
        message_log = '{}'
        logger.debug(message_log.format(function_name))
        # self.send_presence()
        profile.set_identity(self, 'client')
        self['xep_0115'].update_caps()
        bookmarks = await XmppBookmark.get_bookmarks(self)
        await XmppGroupchat.autojoin(self, bookmarks)
        time_end = time.time()
        difference = time_end - time_begin
        if difference > 1: logger.warning('{} (time: {})'.format(function_name,
                                                                 difference))


    async def on_disco_info(self, DiscoInfo):
        time_begin = time.time()
        jid_full = str(DiscoInfo['from'])
        function_name = sys._getframe().f_code.co_name
        message_log = '{}: jid_full: {}'
        logger.debug(message_log.format(function_name, jid_full))
        # self.service_reactions()
        # self.send_presence(pto=jid)
        await self['xep_0115'].update_caps(jid=jid_full)
        time_end = time.time()
        difference = time_end - time_begin
        if difference > 1: logger.warning('{} (time: {})'.format(function_name,
                                                                 difference))


    async def on_message(self, message):
        time_begin = time.time()
        jid_full = str(message['from'])
        function_name = sys._getframe().f_code.co_name
        message_log = '{}: jid_full: {}'
        logger.debug(message_log.format(function_name, jid_full))
        jid_bare = message['from'].bare
        db_file = config.get_pathname_to_database(jid_bare)
        if jid_bare not in self.settings:
            Config.add_settings_jid(self.settings, jid_bare, db_file)
        if jid_bare == self.boundjid.bare:
            status_type = 'dnd'
            status_message = ('Slixfeed is not designed to receive messages '
                              'from itself')
            XmppPresence.send(self, jid_bare, status_message,
                              status_type=status_type)
            await asyncio.sleep(5)
            status_message = ('Slixfeed news bot from RSS Task Force')
            XmppPresence.send(self, jid_bare, status_message)
        else:
            # TODO Request for subscription
            # if (await XmppUtilities.get_chat_type(self, jid_bare) == 'chat' and
            #     not self.client_roster[jid_bare]['to']):
            #     XmppPresence.subscription(self, jid_bare, 'subscribe')
            #     await XmppRoster.add(self, jid_bare)
            #     status_message = '✒️ Share online status to receive updates'
            #     XmppPresence.send(self, jid_bare, status_message)
            #     message_subject = 'RSS News Bot'
            #     message_body = 'Share online status to receive updates.'
            #     XmppMessage.send_headline(self, jid_bare, message_subject,
            #                               message_body, 'chat')
            
            if jid_bare not in self.pending_tasks:
                self.pending_tasks[jid_bare] = {}
            # if jid_full not in self.pending_tasks:
            #     self.pending_tasks[jid_full] = {}
            await XmppChat.process_message(self, message)
        # chat_type = message["type"]
        # message_body = message["body"]
        # message_reply = message.reply
        time_end = time.time()
        difference = time_end - time_begin
        if difference > 1: logger.warning('{} (time: {})'.format(function_name,
                                                                 difference))


    async def on_changed_status(self, presence):
        time_begin = time.time()
        jid_full = str(presence['from'])
        function_name = sys._getframe().f_code.co_name
        message_log = '{}: jid_full: {}'
        logger.debug(message_log.format(function_name, jid_full))
        # await task.check_readiness(self, presence)
        jid_bare = presence['from'].bare
        if jid_bare in self.boundjid.bare:
            return
        if presence['show'] in ('away', 'dnd', 'xa'):
            if (jid_bare in self.task_manager and
                'interval' in self.task_manager[jid_bare]):
                self.task_manager[jid_bare]['interval'].cancel()
            else:
                logger.debug('No task "interval" for JID {} (on_changed_status)'
                             .format(jid_bare))
            XmppStatusTask.restart_task(self, jid_bare)
            FeedTask.restart_task(self, jid_bare)
        time_end = time.time()
        difference = time_end - time_begin
        if difference > 1: logger.warning('{} (time: {})'.format(function_name,
                                                                 difference))


    async def on_presence_subscribe(self, presence):
        time_begin = time.time()
        jid_full = str(presence['from'])
        function_name = sys._getframe().f_code.co_name
        message_log = '{}: jid_full: {}'
        logger.debug(message_log.format(function_name, jid_full))
        jid_bare = presence['from'].bare
        if not self.client_roster[jid_bare]['to']:
        # XmppPresence.subscription(self, jid, 'subscribe')
            XmppPresence.subscription(self, jid_bare, 'subscribed')
            await XmppRoster.add(self, jid_bare)
            status_message = '✒️ Share online status to receive updates'
            XmppPresence.send(self, jid_bare, status_message)
            message_subject = 'RSS News Bot'
            message_body = 'Share online status to receive updates.'
            XmppMessage.send_headline(self, jid_bare, message_subject,
                                      message_body, 'chat')
        time_end = time.time()
        difference = time_end - time_begin
        if difference > 1: logger.warning('{} (time: {})'.format(function_name,
                                                                 difference))


    def on_presence_subscribed(self, presence):
        time_begin = time.time()
        jid_full = str(presence['from'])
        function_name = sys._getframe().f_code.co_name
        message_log = '{}: jid_full: {}'
        logger.debug(message_log.format(function_name, jid_full))
        message_subject = 'RSS News Bot'
        message_body = ('Greetings! I am {}, the news anchor.\n'
                        'My job is to bring you the latest '
                        'news from sources you provide me with.\n'
                        'You may always reach me via xmpp:{}?message'
                        .format(self.alias, self.boundjid.bare))
        jid_bare = presence['from'].bare
        # XmppPresence.subscription(self, jid, 'subscribed')
        XmppMessage.send_headline(self, jid_bare, message_subject,
                                  message_body, 'chat')
        time_end = time.time()
        difference = time_end - time_begin
        if difference > 1: logger.warning('{} (time: {})'.format(function_name,
                                                                 difference))


    async def on_presence_available(self, presence):
        time_begin = time.time()
        jid_full = str(presence['from'])
        function_name = sys._getframe().f_code.co_name
        message_log = '{}: jid_full: {}'
        logger.debug(message_log.format(function_name, jid_full))
        jid_bare = presence['from'].bare
        if jid_bare in self.boundjid.bare:
            return
        # FIXME TODO Find out what is the source responsible for a couple presences with empty message
        # NOTE This is a temporary solution
        await asyncio.sleep(10)
        FeedTask.restart_task(self, jid_bare)
        XmppChatTask.restart_task(self, jid_bare)
        XmppStatusTask.restart_task(self, jid_bare)
        self.add_event_handler("presence_unavailable",
                               self.on_presence_unavailable)
        time_end = time.time()
        difference = time_end - time_begin
        if difference > 15: logger.warning('{}: jid_full: {} (time: {})'
                                           .format(function_name, jid_full,
                                                   difference))


    def on_presence_unsubscribed(self, presence):
        time_begin = time.time()
        jid_full = str(presence['from'])
        function_name = sys._getframe().f_code.co_name
        message_log = '{}: jid_full: {}'
        logger.debug(message_log.format(function_name, jid_full))
        jid_bare = presence['from'].bare
        message_body = 'You have been unsubscribed.'
        # status_message = '🖋️ Subscribe to receive updates'
        # status_message = None
        XmppMessage.send(self, jid_bare, message_body, 'chat')
        XmppPresence.subscription(self, jid_bare, 'unsubscribed')
        # XmppPresence.send(self, jid, status_message,
        #                   presence_type='unsubscribed')
        XmppRoster.remove(self, jid_bare)
        time_end = time.time()
        difference = time_end - time_begin
        if difference > 1: logger.warning('{} (time: {})'.format(function_name,
                                                                 difference))


    def on_presence_unavailable(self, presence):
        time_begin = time.time()
        jid_full = str(presence['from'])
        function_name = sys._getframe().f_code.co_name
        message_log = '{}: jid_full: {}'
        logger.debug(message_log.format(function_name, jid_full))
        jid_bare = presence['from'].bare
        for task in ('check', 'interval', 'status'):
            Task.stop(self, jid_bare, 'status')

        # NOTE Albeit nice to ~have~ see, this would constantly
        #      send presence messages to server to no end.
        status_message = 'Farewell'
        XmppPresence.send(self, jid_bare, status_message,
                          presence_type='unavailable')
        self.del_event_handler("presence_unavailable",
                               self.on_presence_unavailable)
        time_end = time.time()
        difference = time_end - time_begin
        if difference > 1: logger.warning('{} (time: {})'.format(function_name,
                                                                 difference))


    # TODO
    # Send message that database will be deleted within 30 days
    # Check whether JID is in bookmarks or roster
    # If roster, remove contact JID into file 
    # If bookmarks, remove groupchat JID into file 
    def on_presence_error(self, presence):
        time_begin = time.time()
        jid_full = str(presence['from'])
        function_name = sys._getframe().f_code.co_name
        message_log = '{}: jid_full: {}'
        logger.debug(message_log.format(function_name, jid_full))
        jid_bare = presence["from"].bare
        for task in ('check', 'interval', 'status'):
            Task.stop(self, jid_bare, 'status')
        time_end = time.time()
        difference = time_end - time_begin
        if difference > 1: logger.warning('{} (time: {})'.format(function_name,
                                                                 difference))


    def on_reactions(self, message):
        print(message['from'])
        print(message['reactions']['values'])


    async def on_chatstate_active(self, message):
        time_begin = time.time()
        jid_full = str(message['from'])
        function_name = sys._getframe().f_code.co_name
        message_log = '{}: jid_full: {}'
        logger.debug(message_log.format(function_name, jid_full))
        jid_bare = message['from'].bare
        if jid_bare in self.boundjid.bare:
            return
        if message['type'] in ('chat', 'normal'):
            # NOTE: Required for Cheogram
            # await self['xep_0115'].update_caps(jid=jid)
            # self.send_presence(pto=jid)
            # task.clean_tasks_xmpp_chat(self, jid, ['status'])
            await asyncio.sleep(5)
            XmppStatusTask.restart_task(self, jid_bare)
        time_end = time.time()
        difference = time_end - time_begin
        if difference > 10: logger.warning('{} (time: {})'.format(function_name,
                                                                  difference))


    async def on_chatstate_composing(self, message):
        # print('on_chatstate_composing START')
        time_begin = time.time()
        jid_full = str(message['from'])
        function_name = sys._getframe().f_code.co_name
        message_log = '{}: jid_full: {}'
        logger.debug(message_log.format(function_name, jid_full))
        if message['type'] in ('chat', 'normal'):
            jid_bare = message['from'].bare
            # NOTE: Required for Cheogram
            # await self['xep_0115'].update_caps(jid=jid)
            # self.send_presence(pto=jid)
            # task.clean_tasks_xmpp_chat(self, jid, ['status'])
            await asyncio.sleep(5)
            status_message = ('💡 Send "help" for manual, or "info" for '
                              'information.')
            XmppPresence.send(self, jid_bare, status_message)
        # print('on_chatstate_composing FINISH')
        time_end = time.time()
        difference = time_end - time_begin
        if difference > 1: logger.warning('{} (time: {})'.format(function_name,
                                                                 difference))


    def on_chatstate_gone(self, message):
        time_begin = time.time()
        jid_full = str(message['from'])
        function_name = sys._getframe().f_code.co_name
        message_log = '{}: jid_full: {}'
        logger.debug(message_log.format(function_name, jid_full))
        jid_bare = message['from'].bare
        if jid_bare in self.boundjid.bare:
            return
        if message['type'] in ('chat', 'normal'):
            XmppStatusTask.restart_task(self, jid_bare)
        time_end = time.time()
        difference = time_end - time_begin
        if difference > 1: logger.warning('{} (time: {})'.format(function_name,
                                                                 difference))


    def on_chatstate_inactive(self, message):
        time_begin = time.time()
        jid_full = str(message['from'])
        function_name = sys._getframe().f_code.co_name
        message_log = '{}: jid_full: {}'
        logger.debug(message_log.format(function_name, jid_full))
        jid_bare = message['from'].bare
        if jid_bare in self.boundjid.bare:
            return
        if message['type'] in ('chat', 'normal'):
            XmppStatusTask.restart_task(self, jid_bare)
        time_end = time.time()
        difference = time_end - time_begin
        if difference > 1: logger.warning('{} (time: {})'.format(function_name,
                                                                 difference))


    def on_chatstate_paused(self, message):
        time_begin = time.time()
        jid_full = str(message['from'])
        function_name = sys._getframe().f_code.co_name
        message_log = '{}: jid_full: {}'
        logger.debug(message_log.format(function_name, jid_full))
        jid_bare = message['from'].bare
        if jid_bare in self.boundjid.bare:
            return
        if message['type'] in ('chat', 'normal'):
            XmppStatusTask.restart_task(self, jid_bare)
        time_end = time.time()
        difference = time_end - time_begin
        if difference > 1: logger.warning('{} (time: {})'.format(function_name,
                                                                 difference))



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
        form = self['xep_0004'].make_form('form', 'Reactions Information')

############################################################
#                                                          #
#                     INSTRUCTIONS                         #
#                                                          #
############################################################
#
# 1) Best practice: One form per functionality.
# 2) Use match/case only when it is intended to provide
#     several actions of functionality of similar context.
#     This will usually occur from first form which receives
#     the parameters (self, iq, session) to second form which
#     is yielded from a function with match/case.
# 3) Do not use same function for two different actions
#     (i.e. match/case), because it makes context and future
#     management difficult.
#
# TODO
#
# Add intermediate form to separate several forms from a function..
# The intermediate form will have technical explanation about the next form.
#
# e.g when list-multi is engaged
#  options.addOption('Bookmarks', 'bookmarks')
#  options.addOption('Contacts', 'roster')
#  options.addOption('Nodes', 'nodes')
#  options.addOption('PubSub', 'pubsub')
#  options.addOption('Subscribers', 'subscribers')
#
# NOTE
#
# 1) Utilize code session['notes'] to keep last form:
#
# text_note = 'Done.'
# session['next'] = None
# session['notes'] = [['info', text_note]]
# session['payload'] = None
#
# see _handle_subscription_toggle
#
# instead of
#
# form = payload
# form['title'] = 'Done'
# form['instructions'] = None
# session['payload'] = form
#
# 2) Set session['next'] = None to make form to disappear (Cheogram and monocles chat)
#
    def adhoc_commands(self):
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}'.format(function_name))
        # self["xep_0050"].add_command(
        #     node="updates_enable",
        #     name="Enable/Disable News Updates",
        #     handler=option_enable_updates,
        #     )

        # NOTE https://codeberg.org/poezio/slixmpp/issues/3515
        # if is_operator(self, jid_bare):
        self['xep_0050'].add_command(node='subscription',
                                     name='🪶️ Subscribe',
                                     handler=self._handle_subscription_add)
        self['xep_0050'].add_command(node='publish',
                                     name='📣️ Publish',
                                     handler=self._handle_publish)
        self['xep_0050'].add_command(node='recent',
                                     name='📰️ Browse',
                                     handler=self._handle_recent)
        self['xep_0050'].add_command(node='subscriptions',
                                     name='🎫️ Subscriptions',
                                     handler=self._handle_subscriptions)
        self['xep_0050'].add_command(node='promoted',
                                     name='🔮️ Featured',
                                     handler=self._handle_promoted)
        self['xep_0050'].add_command(node='discover',
                                     name='🔍️ Discover',
                                     handler=self._handle_discover)
        self['xep_0050'].add_command(node='settings',
                                     name='📮️ Settings',
                                     handler=self._handle_settings)
        self['xep_0050'].add_command(node='filters',
                                     name='🛡️ Filters',
                                     handler=self._handle_filters)
        self['xep_0050'].add_command(node='help',
                                     name='📔️ Manual',
                                     handler=self._handle_help)
        self['xep_0050'].add_command(node='advanced',
                                     name='📓 Advanced',
                                     handler=self._handle_advanced)
        self['xep_0050'].add_command(node='profile',
                                     name='💼️ Profile',
                                     handler=self._handle_profile)
        self['xep_0050'].add_command(node='about',
                                     name='📜️ About',
                                     handler=self._handle_about)
        # self['xep_0050'].add_command(node='search',
        #                              name='Search',
        #                              handler=self._handle_search)

    # Special interface
    # http://jabber.org/protocol/commands#actions

    async def _handle_publish(self, iq, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = session['from'].bare
        chat_type = await XmppUtilities.get_chat_type(self, jid_bare)
        if is_access(self, jid_bare, jid_full, chat_type):
            form = self['xep_0004'].make_form('form', 'PubSub')
            form['instructions'] = 'Publish news items to PubSub nodes.'
            options = form.add_field(desc='From which medium source do you '
                                          'want to select data to publish?',
                                     ftype='list-single',
                                     label='Source',
                                     required=True,
                                     var='option')
            options.addOption('Database', 'database')
            options.addOption('URL', 'url')
            form.add_field(ftype='fixed',
                           label='* Attention',
                           desc='Results are viewed best with Movim and '
                                'Libervia.')
            session['allow_prev'] = False
            session['has_next'] = True
            session['next'] = self._handle_publish_action
            session['prev'] = None
            session['payload'] = form
        else:
            if not is_operator(self, jid_bare):
                text_warn = 'This resource is restricted to operators.'
            elif chat_type == 'groupchat':
                text_warn = ('This resource is restricted to moderators of {}.'
                             .format(jid_bare))
            elif chat_type == 'error':
                text_warn = ('Could not determine chat type of {}.'
                             .format(jid_bare))
            else:
                text_warn = 'This resource is forbidden.'
            session['notes'] = [['warn', text_warn]]
        return session

    async def _handle_publish_action(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = session['from'].bare
        chat_type = await XmppUtilities.get_chat_type(self, jid_bare)
        if is_access(self, jid_bare, jid_full, chat_type):
            values = payload['values']
            form = self['xep_0004'].make_form('form', 'Publish')
            form['instructions'] = ('Choose a PubSub Jabber ID and verify '
                                    'that Slixfeed has the necessary '
                                    'permissions to publish into it.')
            match values['option']:
                case 'database':
                    session['next'] = self._handle_publish_db_preview
                    options = form.add_field(desc='Select a Jabber ID of '
                                                  'which data you want to '
                                                  'browse (The default Jabber '
                                                  'ID is {}).'
                                                  .format(jid_bare),
                                             ftype='list-single',
                                             label='Jabber ID',
                                             value=jid_bare,
                                             var='jid_bare')
                    jids = []
                    contacts = await XmppRoster.get_contacts(self)
                    for contact in contacts:
                        jids.extend([contact])
                    conferences = await XmppBookmark.get_bookmarks(self)
                    for conference in conferences:
                        jids.extend([conference['jid']])
                    pubsubs = await XmppPubsub.get_pubsub_services(self)
                    for pubsub in pubsubs:
                        jids.extend([pubsub['jid']])
                    for jid_bare in sorted(jids):
                        options.addOption(jid_bare, jid_bare)
                case 'url':
                    session['next'] = self._handle_publish_url_preview
                                           # TODO Make it possible to add several subscriptions at once;
                                           #      Similarly to BitTorrent trackers list
                                           # ftype='text-multi',
                                           # label='Subscription URLs',
                                           # desc='Add subscriptions one time per '
                                           #       'subscription.',
                    form.add_field(desc='Enter a URL.',
                                   ftype='text-single',
                                   label='Subscription',
                                   required=True,
                                   value='http://',
                                   var='url')
            options = form.add_field(desc='Select a PubSub Service.',
                                     ftype='list-single',
                                     label='PubSub',
                                     required=True,
                                     value=self.boundjid.bare,
                                     var='jid')
            options.addOption(self.boundjid.bare, self.boundjid.bare)
            iq = await self['xep_0030'].get_items(jid=self.boundjid.domain)
            items = iq['disco_items']['items']
            for item in items:
                iq = await self['xep_0030'].get_info(jid=item[0])
                identities = iq['disco_info']['identities']
                for identity in identities:
                    if identity[0] == 'pubsub' and identity[1] == 'service':
                        jid = item[0]
                        if item[1]: name = item[1]
                        elif item[2]: name = item[2]
                        else: name = jid
                        options.addOption(jid, name)
            # form.add_field(desc='Enter a PubSub Jabber ID.',
            #                ftype='text-single',
            #                label='PubSub',
            #                required=True,
            #                # value='pubsub.' + self.boundjid.host,
            #                value=self.boundjid.bare,
            #                var='jid')
            form.add_field(desc='Enter a node to publish to.',
                           ftype='text-single',
                           label='Node',
                           var='node')
            # options = form.add_field(desc='Select XMPP Extension Protocol.',
            #                          ftype='list-single',
            #                          label='Protocol',
            #                          required=True,
            #                          value='0060',
            #                          var='xep')
            # options.addOption('XEP-0060: Publish-Subscribe', '0060')
            # options.addOption('XEP-0277: Microblogging over XMPP', '0277')
            # options.addOption('XEP-0472: Pubsub Social Feed', '0472')
            session['payload'] = form
            session['allow_prev'] = True
            session['has_next'] = True
            session['prev'] = self._handle_publish
        else:
            if not is_operator(self, jid_bare):
                text_warn = 'This resource is restricted to operators.'
            elif chat_type == 'groupchat':
                text_warn = ('This resource is restricted to moderators of {}.'
                             .format(jid_bare))
            elif chat_type == 'error':
                text_warn = ('Could not determine chat type of {}.'
                             .format(jid_bare))
            else:
                text_warn = 'This resource is forbidden.'
            session['notes'] = [['warn', text_warn]]
        return session

    async def _handle_publish_db_preview(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        values = payload['values']
        print('_handle_publish_db_preview')
        print(values['jid'])
        jid = values['jid'] if 'jid' in values else None
        jid_bare = session['from'].bare
        if jid != jid_bare and not is_operator(self, jid_bare):
            text_warn = ('Posting to {} is restricted to operators only.'
                         .format(jid_bare)) # Should not this be self.boundjid.bare?
            session['allow_prev'] = False
            session['has_next'] = False
            session['next'] = None
            session['notes'] = [['warn', text_warn]]
            session['prev'] = None
            session['payload'] = None
            return session
        jid_bare = values['jid_bare']
        node = values['node']
        # xep = values['xep']
        if not node:
            if jid == self.boundjid.bare:
                node = 'urn:xmpp:microblog:0'
            else:
                node = 'slixfeed'
        form = self['xep_0004'].make_form('form', 'Publish')

        form.add_field(var='node',
                       ftype='hidden',
                       value=node)
        form.add_field(var='jid',
                       ftype='hidden',
                       value=jid)
        form.add_field(var='jid_bare',
                       ftype='hidden',
                       value=jid_bare)
        num = 100
        db_file = config.get_pathname_to_database(jid_bare)
        results = sqlite.get_entries(db_file, num)
        subtitle = 'Recent {} updates'.format(num)
        if results:
            form['instructions'] = subtitle
            options = form.add_field(desc='Select news items to publish.',
                                     ftype='list-multi',
                                     label='News',
                                     required=True,
                                     var='entries')
            for result in results:
                title = result[1] # TODO Decide what title to display upon empty title
                if not title: title = sqlite.get_feed_title(db_file, result[4])
                ix = str(result[0])
                options.addOption(title, ix)
            session['has_next'] = True
            session['next'] = self._handle_publish_db_complete
            session['payload'] = form
        else:
            text_info = 'There are no news'
            session['has_next'] = False
            session['next'] = None
            session['notes'] = [['info', text_info]]
            session['payload'] = None
        session['allow_prev'] = True
        session['prev'] = self._handle_publish
        return session


    async def _handle_publish_db_complete(self, payload, session):
        values = payload['values']
        jid_bare = values['jid_bare'][0]
        print('jid_bare')
        print(jid_bare)
        print("values['node']")
        print(values['node'])
        node_id = values['node'][0]
        jid = values['jid'][0]
        ixs = values['entries']
        #if jid: jid = jid[0] if isinstance(jid, list) else jid
        jid_bare = session['from'].bare
        if jid != jid_bare and not is_operator(self, jid_bare):
            # TODO Report incident
            text_warn = 'You are not suppose to be here.'
            session['allow_prev'] = False
            session['has_next'] = False
            session['next'] = None
            session['notes'] = [['warn', text_warn]]
            session['prev'] = None
            session['payload'] = None
            return session
        # xep = values['xep'][0]
        # xep = None
        
        for ix in ixs:
            await XmppPubsubAction.send_selected_entry(self, jid, node_id, ix)
            text_info = 'Posted {} entries.'.format(len(ixs))
            session['allow_prev'] = False
            session['has_next'] = False
            session['next'] = None
            session['notes'] = [['info', text_info]]
            session['prev'] = None
            session['payload'] = None
        else:
            session['payload'] = payload
        return session


    async def _handle_publish_url_preview(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        values = payload['values']
        jid = values['jid'] if 'jid' in values else None
        jid_bare = session['from'].bare
        if jid != jid_bare and not is_operator(self, jid_bare):
            # TODO Report incident
            text_warn = 'You are not suppose to be here.'
            # text_warn = ('Posting to {} is restricted to operators only.'
            #              .format(jid_bare)) # Should not this be self.boundjid.bare?
            session['allow_prev'] = False
            session['has_next'] = False
            session['next'] = None
            session['notes'] = [['warn', text_warn]]
            session['prev'] = None
            session['payload'] = None
            return session
        node = values['node']
        url = values['url']
        # xep = values['xep']
        if not node:
            if jid == self.boundjid.bare:
                node = 'urn:xmpp:microblog:0'
            else:
                node = uri.get_hostname(url)
        form = self['xep_0004'].make_form('form', 'Publish')
        while True:
            result = await fetch.http(url)
            status = result['status_code']
            if not result['error']:
                document = result['content']
                feed = parse(document)
                if Feed.is_feed(url, feed):
                    form['instructions'] = 'Select entries to publish.'
                    options = form.add_field(desc='Select entries to post.',
                                             ftype='list-multi',
                                             label='Titles',
                                             required=True,
                                             var='entries')
                    if "title" in feed["feed"].keys():
                        title = feed["feed"]["title"]
                    else:
                        title = uri.get_hostname(url)
                    entries = feed.entries
                    entry_ix = 0
                    for entry in entries:
                        if entry.has_key("title"):
                            title = entry.title
                        else:
                            if entry.has_key("published"):
                                title = entry.published
                                title = dt.rfc2822_to_iso8601(title)
                            elif entry.has_key("updated"):
                                title = entry.updated
                                title = dt.rfc2822_to_iso8601(title)
                            else:
                                title = "*** No title ***"
                        options.addOption(title, str(entry_ix))
                        entry_ix += 1
                        if entry_ix > 9:
                            break
                    session['allow_prev'] = True
                    session['has_next'] = True
                    session['next'] = self._handle_publish_url_complete
                    session['notes'] = None
                    session['prev'] = self._handle_publish
                    session['payload'] = form
                    break
                else:
                    result = await crawl.probe_page(url, document)
                    if isinstance(result, list):
                        results = result
                        form['instructions'] = ('Discovered {} subscriptions '
                                                'for {}'
                                                .format(len(results), url))
                        options = form.add_field(desc='Select a feed.',
                                                 ftype='list-single',
                                                 label='Feeds',
                                                 required=True,
                                                 var='url')
                        for result in results:
                            title = result['name']
                            url = result['link']
                            title = title if title else url
                            options.addOption(title, url)
                        session['allow_prev'] = True
                        session['has_next'] = True
                        session['next'] = self._handle_publish_url_preview
                        session['notes'] = None
                        session['prev'] = self._handle_publish
                        session['payload'] = form
                        break
                    else:
                        url = result['link']
            else:
                text_error = ('Failed to load URL {}'
                              '\n\n'
                              'Reason: {}'
                              .format(url, status))
                session['notes'] = [['error', text_error]]
                session['payload'] = None
                break
        form.add_field(var='node',
                       ftype='hidden',
                       value=node)
        form.add_field(var='jid',
                       ftype='hidden',
                       value=jid)
        # It is essential to place URL at the end, because it might mutate
        # For example http://blacklistednews.com would change
        # to https://www.blacklistednews.com/rss.php
        form.add_field(var='url',
                       ftype='hidden',
                       value=url)
        # form.add_field(var='xep',
        #                ftype='hidden',
        #                value=xep)
        return session
    
    async def _handle_publish_url_complete(self, payload, session):
        values = payload['values']
        entries = values['entries']
        # It might not be good to pass feed object as its size might be too big
        # Consider a handler self.feeds[url][feed] or self.feeds[jid][url][feed]
        # It is not possible to assign non-str to transfer.
        # feed = values['feed']
        node = values['node'][0]
        jid = values['jid'][0] if 'jid' in values else None
        #if jid: jid = jid[0] if isinstance(jid, list) else jid
        jid_bare = session['from'].bare
        if jid != jid_bare and not is_operator(self, jid_bare):
            # TODO Report incident
            text_warn = 'You are not suppose to be here.'
            session['allow_prev'] = False
            session['has_next'] = False
            session['next'] = None
            session['notes'] = [['warn', text_warn]]
            session['prev'] = None
            session['payload'] = None
            return session
        url = values['url'][0]
        # xep = values['xep'][0]
        xep = None
        result = await fetch.http(url)
        if 'content' in result:
            document = result['content']
            feed = parse(document)
            if feed.feed.has_key('title'):
                feed_title = feed.feed.title
            if feed.feed.has_key('description'):
                feed_summary = feed.feed.description
            elif feed.feed.has_key('subtitle'):
                feed_summary = feed.feed.subtitle
            else:
                feed_summary = None
            iq_create_node = XmppPubsub.create_node(
                self, jid, node, xep, feed_title, feed_summary)
            await XmppIQ.send(self, iq_create_node)
            feed_version = feed.version
            for entry in entries:
                entry = int(entry)
                feed_entry = feed.entries[entry]
                # if feed.entries[entry].has_key("title"):
                #     title = feed.entries[entry].title
                # else:
                #     if feed.entries[entry].has_key("published"):
                #         title = feed.entries[entry].published
                #         title = dt.rfc2822_to_iso8601(title)
                #     elif feed.entries[entry].has_key("updated"):
                #         title = feed.entries[entry].updated
                #         title = dt.rfc2822_to_iso8601(title)
                #     else:
                #         title = "*** No title ***"
                # if feed.entries[entry].has_key("summary"):
                #     summary = feed.entries[entry].summary
                iq_create_entry = XmppPubsub._create_entry(
                    self, jid, node, feed_entry, feed_version)
                await XmppIQ.send(self, iq_create_entry)
                text_info = 'Posted {} entries.'.format(len(entries))
                session['allow_prev'] = False
                session['has_next'] = False
                session['next'] = None
                session['notes'] = [['info', text_info]]
                session['prev'] = None
                session['payload'] = None
        else:
            session['payload'] = payload
        return session

    async def _handle_profile(self, iq, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = session['from'].bare
        db_file = config.get_pathname_to_database(jid_bare)
        if jid_bare not in self.settings:
            Config.add_settings_jid(self.settings, jid_bare, db_file)
        form = self['xep_0004'].make_form('form', 'Profile')
        form['instructions'] = ('Displaying information\nJabber ID {}'
                                .format(jid_bare))
        form.add_field(ftype='fixed',
                       label='News')
        feeds_all = str(sqlite.get_number_of_items(db_file, 'feeds_properties'))
        form.add_field(label='Subscriptions',
                       ftype='text-single',
                       value=feeds_all)
        feeds_act = str(sqlite.get_number_of_feeds_active(db_file))
        form.add_field(label='Active',
                       ftype='text-single',
                       value=feeds_act)
        entries = sqlite.get_number_of_items(db_file, 'entries_properties')
        form.add_field(label='Items',
                       ftype='text-single',
                       value=entries)
        unread = str(sqlite.get_number_of_entries_unread(db_file))
        form.add_field(label='Unread',
                       ftype='text-single',
                       value=unread)
        form.add_field(ftype='fixed',
                       label='Options')
        key_archive = Config.get_setting_value(self.settings, jid_bare, 'archive')
        key_archive = str(key_archive)
        form.add_field(label='Archive',
                       ftype='text-single',
                       value=key_archive)
        key_enabled = Config.get_setting_value(self.settings, jid_bare, 'enabled')
        key_enabled = str(key_enabled)
        form.add_field(label='Enabled',
                       ftype='text-single',
                       value=key_enabled)
        key_interval = Config.get_setting_value(self.settings, jid_bare, 'interval')
        key_interval = str(key_interval)
        form.add_field(label='Interval',
                       ftype='text-single',
                       value=key_interval)
        key_length = Config.get_setting_value(self.settings, jid_bare, 'length')
        key_length = str(key_length)
        form.add_field(label='Length',
                       ftype='text-single',
                       value=key_length)
        key_media = Config.get_setting_value(self.settings, jid_bare, 'media')
        key_media = str(key_media)
        form.add_field(label='Media',
                       ftype='text-single',
                       value=key_media)
        key_old = Config.get_setting_value(self.settings, jid_bare, 'old')
        key_old = str(key_old)
        form.add_field(label='Old',
                       ftype='text-single',
                       value=key_old)
        key_quantum = Config.get_setting_value(self.settings, jid_bare, 'quantum')
        key_quantum = str(key_quantum)
        form.add_field(label='Quantum',
                       ftype='text-single',
                       value=key_quantum)
        update_interval = Config.get_setting_value(self.settings, jid_bare, 'interval')
        update_interval = str(update_interval)
        update_interval = 60 * int(update_interval)
        last_update_time = sqlite.get_last_update_time(db_file)
        if last_update_time:
            last_update_time = float(last_update_time)
            dt_object = datetime.fromtimestamp(last_update_time)
            last_update = dt_object.strftime('%H:%M:%S')
            if int(key_enabled):
                next_update_time = last_update_time + update_interval
                dt_object = datetime.fromtimestamp(next_update_time)
                next_update = dt_object.strftime('%H:%M:%S')
            else:
                next_update = 'n/a'
        else:
            last_update = 'n/a'
            next_update = 'n/a'
        form.add_field(ftype='fixed',
                       label='Schedule')
        form.add_field(label='Last update',
                       ftype='text-single',
                       value=last_update)
        form.add_field(label='Next update',
                       ftype='text-single',
                       value=next_update)
        session['payload'] = form
        # text_note = ('Jabber ID: {}'
        #              '\n'
        #              'Last update: {}'
        #              '\n'
        #              'Next update: {}'
        #              ''.format(jid, last_update, next_update))
        # session['notes'] = [['info', text_note]]
        return session

    async def _handle_filters(self, iq, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = session['from'].bare
        chat_type = await XmppUtilities.get_chat_type(self, jid_bare)
        if is_access(self, jid_bare, jid_full, chat_type):
            jid = session['from'].bare
            db_file = config.get_pathname_to_database(jid_bare)
            form = self['xep_0004'].make_form('form', 'Filters')
            form['instructions'] = ('Filters allow you to skip news items '
                                    'that you may not be interested at. Use '
                                    'the "Exception list" to exceptionally '
                                    'enforce items that contain keywords of '
                                    'the "Deny list". Use the "Allow list" to '
                                    'skip any item that does not include the '
                                    'chosen keywords')
            value = sqlite.get_filter_value(db_file, 'allow')
            if value: value = str(value[0])
            form.add_field(desc='Keywords to allow (comma-separated keywords).',
                           ftype='text-single',
                           label='Allow list',
                           value=value,
                           var='allow')
            form.add_field(ftype='fixed',
                           label='* Attention',
                           desc='The "Allow list" will skip any item that '
                           'does not include its keywords.')
            value = sqlite.get_filter_value(db_file, 'deny')
            if value: value = str(value[0])
            form.add_field(desc='Keywords to deny (comma-separated keywords).',
                           ftype='text-single',
                           label='Deny list',
                           value=value,
                           var='deny')
            form.add_field(desc='Keywords to enforce (comma-separated keywords).',
                           ftype='text-single',
                           label='Exception list',
                           value=value,
                           var='exception')
            session['allow_complete'] = True
            session['has_next'] = False
            session['next'] = self._handle_filters_complete
            session['payload'] = form
        else:
            if not is_operator(self, jid_bare):
                text_warn = 'This resource is restricted to operators.'
            elif chat_type == 'groupchat':
                text_warn = ('This resource is restricted to moderators of {}.'
                             .format(jid_bare))
            elif chat_type == 'error':
                text_warn = ('Could not determine chat type of {}.'
                             .format(jid_bare))
            else:
                text_warn = 'This resource is forbidden.'
            session['notes'] = [['warn', text_warn]]
        return session


    async def _handle_filters_complete(self, payload, session):
        """
        Process a command result from the user.

        Arguments:
            payload -- Either a single item, such as a form, or a list
                       of items or forms if more than one form was
                       provided to the user. The payload may be any
                       stanza, such as jabber:x:oob for out of band
                       data, or jabber:x:data for typical data forms.
            session -- A dictionary of data relevant to the command
                       session. Additional, custom data may be saved
                       here to persist across handler callbacks.
        """
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        # Text is not displayed; only labels
        form = payload

        jid_bare = session['from'].bare
        # form = self['xep_0004'].make_form('result', 'Done')
        # form['instructions'] = ('✅️ Filters have been updated')
        db_file = config.get_pathname_to_database(jid_bare)
        # In this case (as is typical), the payload is a form
        values = payload['values']
        for key in values:
            val = values[key]
            # NOTE We might want to add new keywords from
            #      an empty form instead of editing a form.
            # keywords = sqlite.get_filter_value(db_file, key)
            keywords = ''
            val = await config.add_to_list(val, keywords) if val else ''
            if sqlite.is_filter_key(db_file, key):
                await sqlite.update_filter_value(db_file, [key, val])
            elif val:
                await sqlite.set_filter_value(db_file, [key, val])
            # form.add_field(var=key.capitalize() + ' list',
            #                ftype='text-single',
            #                value=val)
        form['title'] = 'Done'
        form['instructions'] = 'has been completed!'
        # session["has_next"] = False
        session['next'] = None
        session['payload'] = form
        return session


    async def _handle_subscription_add(self, iq, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = session['from'].bare
        chat_type = await XmppUtilities.get_chat_type(self, jid_bare)
        if is_access(self, jid_bare, jid_full, chat_type):
            form = self['xep_0004'].make_form('form', 'Subscribe')
            # form['instructions'] = 'Add a new custom subscription.'
            form.add_field(desc='Enter a URL.',
                           # TODO Make it possible to add several subscriptions at once;
                           #      Similarly to BitTorrent trackers list
                           # ftype='text-multi',
                           # label='Subscription URLs',
                           # desc='Add subscriptions one time per '
                           #       'subscription.',
                           ftype='text-single',
                           label='Subscription',
                           required=True,
                           value='http://',
                           var='subscription')
            if is_operator(self, jid_bare):
                # form['instructions'] = ('Special section for operators:\n'
                #                         'This section allows you to add '
                #                         'subscriptions for a JID of your '
                #                         'choice.')
                form.add_field(ftype='fixed',
                               label='* Operators',
                               desc='This section allows you to add '
                               'subscriptions for a JID of your '
                               'choice.')
                form.add_field(desc='Enter a Jabber ID to add the '
                               'subscription to (The default Jabber ID is '
                               'your own).',
                               ftype='text-single',
                               label='Subscriber',
                               var='jid')
            # form.add_field(desc='Scan URL for validity (recommended).',
            #                ftype='boolean',
            #                label='Scan',
            #                value=True,
            #                var='scan')
            session['allow_prev'] = False
            session['has_next'] = True
            session['next'] = self._handle_subscription_new
            session['prev'] = None
            session['payload'] = form
        else:
            if not is_operator(self, jid_bare):
                text_warn = 'This resource is restricted to operators.'
            elif chat_type == 'groupchat':
                text_warn = ('This resource is restricted to moderators of {}.'
                             .format(jid_bare))
            elif chat_type == 'error':
                text_warn = ('Could not determine chat type of {}.'
                             .format(jid_bare))
            else:
                text_warn = 'This resource is forbidden.'
            session['notes'] = [['warn', text_warn]]
        return session


    async def _handle_recent(self, iq, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = session['from'].bare
        form = self['xep_0004'].make_form('form', 'Updates')
        # form['instructions'] = 'Browse and read news items.'
        options = form.add_field(desc='What would you want to read?',
                                 ftype='list-single',
                                 label='News',
                                 required=True,
                                 var='action')
        options.addOption('All', 'all')
        # options.addOption('News by subscription', 'feed')
        # options.addOption('News by tag', 'tag')
        options.addOption('Rejected', 'reject')
        options.addOption('Unread', 'unread')
        if is_operator(self, jid_bare):
            # form['instructions'] = ('Special section for operators:\n'
            #                         'This section allows you to view news items '
            #                         'of a JID of your choice.')
            form.add_field(ftype='fixed',
                            label='* Operators',
                            desc='This section allows you to view news items '
                            'of a JID of your choice.')
            options = form.add_field(desc='Select a Jabber ID.',
                                     ftype='list-single',
                                     label='Subscriber',
                                     value=jid_bare,
                                     var='jid')
            jids = []
            contacts = await XmppRoster.get_contacts(self)
            for contact in contacts:
                jids.extend([contact])
            conferences = await XmppBookmark.get_bookmarks(self)
            for conference in conferences:
                jids.extend([conference['jid']])
            pubsubs = await XmppPubsub.get_pubsub_services(self)
            for pubsub in pubsubs:
                jids.extend([pubsub['jid']])
            for jid_bare in sorted(jids):
                options.addOption(jid_bare, jid_bare)
        session['allow_prev'] = False # Cheogram changes style if that button - which should not be on this form - is present
        session['has_next'] = True
        session['next'] = self._handle_recent_result
        session['payload'] = form
        session['prev'] = None # Cheogram works as expected with 'allow_prev' set to False Just in case
        return session


    async def _handle_recent_result(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = session['from'].bare
        values = payload['values']
        form = self['xep_0004'].make_form('form', 'Updates')
        if is_operator(self, jid_bare) and 'jid' in values:
            jid_bare = values['jid']
            form.add_field(var='jid',
                           ftype='hidden',
                           value=jid_bare)
        db_file = config.get_pathname_to_database(jid_bare)
        num = 100
        match values['action']:
            case 'all':
                results = sqlite.get_entries(db_file, num)
                subtitle = 'Recent {} updates'.format(num)
                message = 'There are no news'
            case 'reject':
                results = sqlite.get_entries_rejected(db_file, num)
                subtitle = 'Recent {} updates (rejected)'.format(num)
                message = 'There are no rejected news'
            case 'unread':
                results = sqlite.get_unread_entries(db_file, num)
                subtitle = 'Recent {} updates (unread)'.format(num)
                message = 'There are no unread news.'
        if results:
            form['instructions'] = subtitle
            options = form.add_field(desc='Select a news item to read.',
                                     ftype='list-single',
                                     label='News',
                                     required=True,
                                     var='update')
            for result in results:
                title = result[1] # TODO Decide what title to display upon empty title
                if not title: title = sqlite.get_feed_title(db_file, result[4])
                ix = str(result[0])
                options.addOption(title, ix)
            session['allow_prev'] = False # Cheogram changes style if that button - which should not be on this form - is present
            session['has_next'] = True
            session['next'] = self._handle_recent_select
            session['payload'] = form
            session['prev'] = None # Cheogram works as expected with 'allow_prev' set to False Just in case
        else:
            text_info = message
            session['allow_prev'] = True
            session['has_next'] = False
            session['next'] = None
            session['notes'] = [['info', text_info]]
            session['payload'] = None
            session['prev'] = self._handle_recent
        return session


    # FIXME
    async def _handle_recent_select(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        values = payload['values']
        ix = values['update']
        jid_bare = session['from'].bare
        form = self['xep_0004'].make_form('form', 'Article')
        if is_operator(self, jid_bare) and 'jid' in values:
            jid = values['jid']
            jid_bare = jid[0] if isinstance(jid, list) else jid
            form.add_field(var='jid',
                           ftype='hidden',
                           value=jid)
        db_file = config.get_pathname_to_database(jid_bare)
        title = sqlite.get_entry_title(db_file, ix)
        title = title[0] if title else 'Untitled'
        form['instructions'] = title
        url = sqlite.get_entry_url(db_file, ix)
        url = url[0] # TODO Handle a situation when index is no longer exist
        logger.debug('Original URL: {}'.format(url))
        url = uri.remove_tracking_parameters(url)
        logger.debug('Processed URL (tracker removal): {}'.format(url))
        url = (await uri.replace_hostname(url, 'link')) or url
        logger.debug('Processed URL (replace hostname): {}'.format(url))
        # result = await fetch.http(url)
        # if 'content' in result:
        #     data = result['content']
        #     summary = action.get_document_content_as_text(data)
        summary = sqlite.get_entry_summary(db_file, ix)
        summary = summary[0]
        summary = Html.remove_html_tags(summary) if summary else 'No content to show.'
        form.add_field(ftype="text-multi",
                       label='Article',
                       value=summary)
        field_url = form.add_field(ftype='hidden',
                                   value=url,
                                   var='url')
        field_url = form.add_field(ftype='text-single',
                                   label='Link',
                                   value=url,
                                   var='url_link')
        field_url['validate']['datatype'] = 'xs:anyURI'
        feed_id = sqlite.get_feed_id_by_entry_index(db_file, ix)
        feed_id = feed_id[0]
        feed_url = sqlite.get_feed_url(db_file, feed_id)
        feed_url = feed_url[0]
        field_feed = form.add_field(ftype='text-single',
                                    label='Source',
                                    value=feed_url,
                                    var='url_feed')
        field_feed['validate']['datatype'] = 'xs:anyURI'
        # options = form.add_field(desc='Select file type.',
        #                          ftype='list-single',
        #                          label='Save as',
        #                          required=True,
        #                          value='pdf',
        #                          var='filetype')
        # options.addOption('ePUB', 'epub')
        # options.addOption('HTML', 'html')
        # options.addOption('Markdown', 'md')
        # options.addOption('PDF', 'pdf')
        # options.addOption('Plain Text', 'txt')
        session['allow_complete'] = False
        session['allow_prev'] = True
        session['has_next'] = True
        # session['next'] = self._handle_recent_action
        session['payload'] = form
        session['prev'] = self._handle_recent
        return session


    async def _handle_subscription_new(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        form = self['xep_0004'].make_form('form', 'Subscription')
        # scan = values['scan']
        values = payload['values']
        identifier = values['identifier'] if 'identifier' in values else None
        url = values['subscription']
        jid_bare = session['from'].bare
        if is_operator(self, jid_bare) and 'jid' in values:
            custom_jid = values['jid']
            jid_bare = custom_jid[0] if isinstance(custom_jid, list) else jid_bare
            # jid_bare = custom_jid[0] if custom_jid else jid_bare
            form.add_field(var='jid',
                           ftype='hidden',
                           value=jid_bare)
        db_file = config.get_pathname_to_database(jid_bare)
        if identifier and sqlite.check_identifier_exist(db_file, identifier):
            form['title'] = 'Conflict'
            form['instructions'] = ('Name "{}" already exists. Choose a '
                                    'different name.')
            form.add_field(desc='Enter a unique identifier. The identifier '
                           'is realized to distinct PubSub nodes.',
                           ftype='text-single',
                           label='identifier',
                           value=identifier,
                           var='identifier')
            form.add_field(ftype='hidden',
                           value=url,
                           var='subscription')
            form.add_field(ftype='hidden',
                           value=identifier,
                           var='identifier')
            session['allow_prev'] = False
            session['next'] = self._handle_subscription_new
            # session['payload'] = None
            session['prev'] = None
        # elif not identifier:
        #     counter = 0
        #     hostname = uri.get_hostname(url)
        #     identifier = hostname + ':' + str(counter)
        #     while True:
        #         if sqlite.check_identifier_exist(db_file, identifier):
        #             counter += 1
        #             identifier = hostname + ':' + str(counter)
        #         else:
        #             break
        # Several URLs to subscribe
        if isinstance(url, list) and len(url) > 1:
            url_count = len(url)
            urls = url
            agree_count = 0
            error_count = 0
            exist_count = 0
            for url in urls:
                counter = 0
                hostname = uri.get_hostname(url)
                identifier = hostname + ':' + str(counter)
                while True:
                    if sqlite.check_identifier_exist(db_file, identifier):
                        counter += 1
                        identifier = hostname + ':' + str(counter)
                    else:
                        break
                result = await Feed.add_feed(self, jid_bare, db_file, url,
                                             identifier)
                if result['error']:
                    error_count += 1
                elif result['exist']:
                    exist_count += 1
                else:
                    agree_count += 1
            if agree_count:
                response = ('Added {} new subscription(s) out of {}'
                            .format(agree_count, url_count))
                session['notes'] = [['info', response]]
            else:
                response = ('No new subscription was added. '
                            'Exist: {} Error: {}.'
                            .format(exist_count, error_count))
                session['notes'] = [['error', response]]
            session['allow_prev'] = True
            session['next'] = None
            session['payload'] = None
            session['prev'] = self._handle_subscription_add
        else:
            if isinstance(url, list):
                url = url[0]
            counter = 0
            hostname = uri.get_hostname(url)
            identifier = hostname + ':' + str(counter)
            while True:
                if sqlite.check_identifier_exist(db_file, identifier):
                    counter += 1
                    identifier = hostname + ':' + str(counter)
                else:
                    break
            result = await Feed.add_feed(self, jid_bare, db_file, url,
                                         identifier)
            # URL is not a feed and URL has returned to feeds
            if isinstance(result, list):
                results = result
                form['instructions'] = ('Discovered {} subscriptions for {}'
                                        .format(len(results), url))
                options = form.add_field(desc='Select subscriptions to add.',
                                         ftype='list-multi',
                                         label='Subscribe',
                                         required=True,
                                         var='subscription')
                for result in results:
                    options.addOption(result['name'], result['link'])
                # NOTE Disabling "allow_prev" until Cheogram would allow to display
                # items of list-single as buttons when button "back" is enabled.
                # session['allow_prev'] = True
                session['has_next'] = True
                session['next'] = self._handle_subscription_new
                session['payload'] = form
                # session['prev'] = self._handle_subscription_add
            elif result['error']:
                response = ('Failed to load resource.'
                            '\n'
                            'URL {}'
                            '\n'
                            'Reason: {}'
                            '\n'
                            'Code: {}'
                            .format(url, result['message'], result['code']))
                session['allow_prev'] = True
                session['next'] = None
                session['notes'] = [['error', response]]
                session['payload'] = None
                session['prev'] = self._handle_subscription_add
            elif result['exist']:
                name = result['name']
                form['instructions'] = ('Subscription "{}" already exist. '
                                        'Proceed to edit this subscription.'
                                        .format(name))
                url = result['link']
                feed_id = str(result['index'])
                entries = sqlite.get_entries_of_feed(db_file, feed_id)
                renewed, scanned = sqlite.get_last_update_time_of_feed(db_file,
                                                                     feed_id)
                last_updated = renewed or scanned
                last_updated = str(last_updated)
                options = form.add_field(desc='Recent titles from subscription',
                                         ftype='list-multi',
                                         label='Preview')
                for entry in entries:
                    options.addOption(entry[1], entry[2])
                form.add_field(ftype='fixed',
                               label='Information')
                form.add_field(ftype='text-single',
                               label='Renewed',
                               value=last_updated)
                form.add_field(ftype='text-single',
                               label='ID #',
                               value=feed_id)
                form.add_field(var='subscription',
                               ftype='hidden',
                               value=url)
                # NOTE Should we allow "Complete"?
                # Do all clients provide button "Cancel".
                session['allow_complete'] = False
                session['has_next'] = True
                session['next'] = self._handle_subscription_edit
                session['payload'] = form
                # session['has_next'] = False
            # Single URL to subscribe
            else:
                print(result)
                name = result['name']
                form['instructions'] = ('Subscription "{}" has been added. '
                                        'Proceed to edit this subscription.'
                                        .format(name))
                url = result['link']
                feed_id = str(result['index'])
                entries = sqlite.get_entries_of_feed(db_file, feed_id)
                renewed, scanned = sqlite.get_last_update_time_of_feed(db_file,
                                                                     feed_id)
                last_updated = renewed or scanned
                last_updated = str(last_updated)
                options = form.add_field(desc='Recent titles from subscription',
                                         ftype='list-multi',
                                         label='Preview')
                for entry in entries:
                    options.addOption(entry[1], entry[2])
                form.add_field(ftype='fixed',
                               label='Information')
                form.add_field(ftype='text-single',
                               label='Updated',
                               value=last_updated)
                form.add_field(ftype='text-single',
                               label='ID #',
                               value=feed_id)
                form.add_field(var='subscription',
                               ftype='hidden',
                               value=url)
                session['allow_complete'] = False
                session['has_next'] = True
                # session['allow_prev'] = False
                # Gajim: Will offer next dialog but as a result, not as form.
                # session['has_next'] = False
                session['next'] = self._handle_subscription_edit
                session['payload'] = form
                # session['prev'] = None
        return session


    async def _handle_subscription_toggle(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = session['from'].bare
        values = payload['values']
        if is_operator(self, jid_bare) and 'jid' in values:
            jid_bare = values['jid'][0]
            del values['jid']
        db_file = config.get_pathname_to_database(jid_bare)
        for key in values:
            value = 1 if values[key] else 0
            await sqlite.set_enabled_status(db_file, key, value)
        # text_note = 'Done.'
        # session['next'] = None
        # session['notes'] = [['info', text_note]]
        # session['payload'] = None
        form = payload
        form['title'] = 'Done'
        form['instructions'] = 'has been successful'
        session['payload'] = form
        return session


    async def _handle_subscription_del_complete(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = session['from'].bare
        values = payload['values']
        if is_operator(self, jid_bare) and 'jid' in values:
            jid_bare = values['jid'][0]
            del values['jid']
        db_file = config.get_pathname_to_database(jid_bare)
        subscriptions =''
        ixs = values['subscriptions']
        for ix in ixs:
            name = sqlite.get_feed_title(db_file, ix)
            url = sqlite.get_feed_url(db_file, ix)
            name = name[0] if name else 'Subscription #{}'.format(ix)
            url = url[0]
            await sqlite.remove_feed_by_index(db_file, ix)
            subscriptions += '{}. {}\n{}\n\n'.format(ix, name, url)
        text_note = ('The following subscriptions have been deleted:\n\n{}'
                     .format(subscriptions))
        session['next'] = None
        session['notes'] = [['info', text_note]]
        session['payload'] = None
        return session


    def _handle_cancel(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        text_note = ('Operation has been cancelled.'
                     '\n'
                     '\n'
                     'No action was taken.')
        session['notes'] = [['info', text_note]]
        return session


    async def _handle_discover(self, iq, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = session['from'].bare
        chat_type = await XmppUtilities.get_chat_type(self, jid_bare)
        if is_access(self, jid_bare, jid_full, chat_type):
            form = self['xep_0004'].make_form('form', 'Discover & Search')
            form['instructions'] = 'Discover news subscriptions of all kinds'
            options = form.add_field(desc='Select type of search.',
                                     ftype='list-single',
                                     label='Browse',
                                     required=True,
                                     var='search_type')
            options.addOption('All', 'all')
            options.addOption('Categories', 'cat') # Should we write this in a singular form
            # options.addOption('Tags', 'tag')
            session['allow_prev'] = False
            session['has_next'] = True
            session['next'] = self._handle_discover_type
            session['payload'] = form
            session['prev'] = None
        else:
            if not is_operator(self, jid_bare):
                text_warn = 'This resource is restricted to operators.'
            elif chat_type == 'groupchat':
                text_warn = ('This resource is restricted to moderators of {}.'
                             .format(jid_bare))
            elif chat_type == 'error':
                text_warn = ('Could not determine chat type of {}.'
                             .format(jid_bare))
            else:
                text_warn = 'This resource is forbidden.'
            session['notes'] = [['warn', text_warn]]
        return session


    def _handle_discover_type(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        values = payload['values']
        search_type = values['search_type']
        config_dir = config.get_default_config_directory()
        db_file = config_dir + '/feeds.sqlite'
        if os.path.isfile(db_file):
            form = self['xep_0004'].make_form('form', 'Discover & Search')
            match search_type:
                case 'all':
                    form['instructions'] = 'Browsing subscriptions'
                    options = form.add_field(desc='Select a subscription to add.',
                                             # ftype='list-multi', # TODO To be added soon
                                             ftype='list-single',
                                             label='Subscription',
                                             required=True,
                                             var='subscription')
                    results = sqlite.get_titles_tags_urls(db_file)
                    for result in results:
                        title = result[0]
                        tag = result[1]
                        url = result[2]
                        text = '{} ({})'.format(title, tag)
                        options.addOption(text, url)
                    # session['allow_complete'] = True
                    session['next'] = self._handle_subscription_new
                case 'cat':
                    form['instructions'] = 'Browsing categories'
                    session['next'] = self._handle_discover_category
                    options = form.add_field(desc='Select a category to browse.',
                                             ftype='list-single',
                                             label='Categories',
                                             required=True,
                                             var='category') # NOTE Uncategories or no option for entries without category
                    categories = sqlite.get_categories(db_file)
                    for category in categories:
                        category = category[0]
                        options.addOption(category, category)
                # case 'tag':
            session['allow_prev'] = True
            session['has_next'] = True
            session['payload'] = form
            session['prev'] = self._handle_discover
        else:
            text_note = ('Database is missing.'
                         '\n'
                         'Contact operator.')
            session['next'] = None
            session['notes'] = [['info', text_note]]
            session['payload'] = None
        return session


    async def _handle_discover_category(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        values = payload['values']
        category = values['category']
        config_dir = config.get_default_config_directory()
        db_file = config_dir + '/feeds.sqlite'
        form = self['xep_0004'].make_form('form', 'Discover & Search')
        form['instructions'] = 'Browsing category "{}"'.format(category)
        options = form.add_field(desc='Select a subscription to add.',
                                 # ftype='list-multi', # TODO To be added soon
                                 ftype='list-single',
                                 label='Subscription',
                                 required=True,
                                 var='subscription')
        results = sqlite.get_titles_tags_urls_by_category(db_file, category)
        for result in results:
            title = result[0]
            tag = result[1]
            url = result[2]
            text = '{} ({})'.format(title, tag)
            options.addOption(text, url)
        # session['allow_complete'] = True
        session['next'] = self._handle_subscription_new
        session['payload'] = form
        return session


    async def _handle_subscriptions(self, iq, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = session['from'].bare
        chat_type = await XmppUtilities.get_chat_type(self, jid_bare)
        if is_access(self, jid_bare, jid_full, chat_type):
            form = self['xep_0004'].make_form('form', 'Subscriptions')
            form['instructions'] = ('Browse, view, toggle or remove '
                                    'tags and subscriptions.')
            options = form.add_field(desc='Select action type.',
                                     ftype='list-single',
                                     label='Action',
                                     required=True,
                                     value='browse',
                                     var='action')
            options.addOption('Browse subscriptions', 'browse')
            options.addOption('Browse tags', 'tag')
            options.addOption('Remove subscriptions', 'delete')
            options.addOption('Toggle subscriptions', 'toggle')
            if is_operator(self, jid_bare):
                form['instructions'] = None
                # form['instructions'] = ('Special section for operators:\n'
                #                         'This section allows you to change '
                #                         'and meddle with subscribers data.')
                form.add_field(ftype='fixed',
                                label='* Operators',
                                desc='This section allows you to change '
                                'subscribers data.')
                options = form.add_field(desc='Select a Jabber ID.',
                                         ftype='list-single',
                                         label='Subscribers',
                                         value=jid_bare,
                                         var='jid')
                jids = []
                contacts = await XmppRoster.get_contacts(self)
                for contact in contacts:
                    jids.extend([contact])
                conferences = await XmppBookmark.get_bookmarks(self)
                for conference in conferences:
                    jids.extend([conference['jid']])
                pubsubs = await XmppPubsub.get_pubsub_services(self)
                for pubsub in pubsubs:
                    jids.extend([pubsub['jid']])
                for jid_bare in sorted(jids):
                    options.addOption(jid_bare, jid_bare)
            session['payload'] = form
            session['next'] = self._handle_subscriptions_result
            session['has_next'] = True
        else:
            if not is_operator(self, jid_bare):
                text_warn = 'This resource is restricted to operators.'
            elif chat_type == 'groupchat':
                text_warn = ('This resource is restricted to moderators of {}.'
                             .format(jid_bare))
            elif chat_type == 'error':
                text_warn = ('Could not determine chat type of {}.'
                             .format(jid_bare))
            else:
                text_warn = 'This resource is forbidden.'
            session['notes'] = [['warn', text_warn]]
        return session


    async def _handle_subscriptions_result(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        values = payload['values']
        jid_bare = session['from'].bare
        form = self['xep_0004'].make_form('form', 'Subscriptions')
        if is_operator(self, jid_bare) and 'jid' in values:
            jid_bare = values['jid']
            form.add_field(ftype='hidden',
                           value=jid_bare,
                           var='jid')
        db_file = config.get_pathname_to_database(jid_bare)
        match values['action']:
            case 'browse':
                form['instructions'] = 'Editing subscriptions'
                options = form.add_field(desc='Select a subscription to edit.',
                                         # ftype='list-multi', # TODO To be added soon
                                         ftype='list-single',
                                         label='Subscription',
                                         required=True,
                                         var='subscriptions')
                subscriptions = sqlite.get_feeds(db_file)
                # subscriptions = sorted(subscriptions, key=lambda x: x[1])
                for subscription in subscriptions:
                    title = subscription[1]
                    url = subscription[2]
                    options.addOption(title, url)
                session['has_next'] = True
                session['next'] = self._handle_subscription_edit
                session['allow_complete'] = False
            case 'delete':
                form['instructions'] = 'Removing subscriptions'
                # form.addField(var='interval',
                #               ftype='text-single',
                #               label='Interval period')
                options = form.add_field(desc='Select subscriptions to remove.',
                                         ftype='list-multi',
                                         label='Subscriptions',
                                         required=True,
                                         var='subscriptions')
                subscriptions = sqlite.get_feeds(db_file)
                # subscriptions = sorted(subscriptions, key=lambda x: x[1])
                for subscription in subscriptions:
                    title = subscription[1]
                    ix = str(subscription[0])
                    options.addOption(title, ix)
                session['cancel'] = self._handle_cancel
                session['has_next'] = False
                # TODO Refer to confirmation dialog which would display feeds selected
                session['next'] = self._handle_subscription_del_complete
                session['allow_complete'] = True
            case 'toggle':
                form['instructions'] = 'Toggling subscriptions'
                subscriptions = sqlite.get_feeds_and_enabled_state(db_file)
                # subscriptions = sorted(subscriptions, key=lambda x: x[1])
                for subscription in subscriptions:
                    ix = str(subscription[0])
                    title = subscription[3]
                    url = subscription[1]
                    enabled_state = True if subscription[17] else False
                    enabled_state = subscription[17]
                    form.add_field(desc=url,
                                   ftype='boolean',
                                   label=title,
                                   value=enabled_state,
                                   var=ix)
                session['cancel'] = self._handle_cancel
                session['has_next'] = False
                session['next'] = self._handle_subscription_toggle
                session['allow_complete'] = True
            case 'tag':
                form['instructions'] = 'Browsing tags'
                options = form.add_field(desc='Select a tag to browse.',
                                         ftype='list-single',
                                         label='Tag',
                                         required=True,
                                         var='tag')
                tags = sqlite.get_tags(db_file)
                # tags = sorted(tags, key=lambda x: x[0])
                for tag in tags:
                    name = tag[0]
                    ix = str(tag[1])
                    options.addOption(name, ix)
                session['allow_complete'] = False
                session['next'] = self._handle_subscription_tag
                session['has_next'] = True
        session['allow_prev'] = True
        session['payload'] = form
        session['prev'] = self._handle_subscriptions
        return session


    async def _handle_subscription_tag(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        form = self['xep_0004'].make_form('form', 'Subscriptions')
        jid_bare = session['from'].bare
        values = payload['values']
        if is_operator(self, jid_bare) and 'jid' in values:
            jid_bare = values['jid'][0]
            form.add_field(ftype='hidden',
                           value=jid_bare,
                           var='jid')
        db_file = config.get_pathname_to_database(jid_bare)
        tag_id = values['tag']
        tag_name = sqlite.get_tag_name(db_file, tag_id)[0]
        form['instructions'] = 'Subscriptions tagged with "{}"'.format(tag_name)
        options = form.add_field(desc='Select a subscription to edit.',
                                 # ftype='list-multi', # TODO To be added soon
                                 ftype='list-single',
                                 label='Subscription',
                                 required=True,
                                 var='subscriptions')
        subscriptions = sqlite.get_feeds_by_tag_id(db_file, tag_id)
        # subscriptions = sorted(subscriptions, key=lambda x: x[1])
        for subscription in subscriptions:
            title = subscription[1]
            url = subscription[2]
            options.addOption(title, url)
        session['allow_complete'] = False
        session['allow_prev'] = True
        session['has_next'] = True
        session['next'] = self._handle_subscription_edit
        session['payload'] = form
        session['prev'] = self._handle_subscriptions
        return session


    async def _handle_subscription_edit(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        form = self['xep_0004'].make_form('form', 'Subscription')
        jid_bare = session['from'].bare
        values = payload['values']
        if is_operator(self, jid_bare) and 'jid' in values:
            jid_bare = values['jid'][0] if values['jid'] else jid_bare
            form.add_field(ftype='hidden',
                           value=jid_bare,
                           var='jid')
        db_file = config.get_pathname_to_database(jid_bare)
        if 'subscription' in values: urls = values['subscription']
        elif 'subscriptions' in values: urls = values['subscriptions']
        url_count = len(urls)
        if isinstance(urls, list) and url_count > 1:
            form['instructions'] = 'Editing {} subscriptions'.format(url_count)
        else:
            if isinstance(urls, list):
                url = urls[0]
            # elif isinstance(urls, str):
            else:
                url = urls
            feed_id = sqlite.get_feed_id(db_file, url)
            if feed_id:
                feed_id = feed_id[0]
                title = sqlite.get_feed_title(db_file, feed_id)
                title = title[0]
                tags_result = sqlite.get_tags_by_feed_id(db_file, feed_id)
                # tags_sorted = sorted(x[0] for x in tags_result)
                # tags = ', '.join(tags_sorted)
                tags = ''
                for tag in tags_result: tags += tag[0] + ', '
                form['instructions'] = 'Editing subscription #{}'.format(feed_id)
            else:
                form['instructions'] = 'Adding subscription'
                title = ''
                tags = '' # TODO Suggest tags by element "categories"
            form.add_field(ftype='fixed',
                           label='Properties')
            form.add_field(var='name',
                           ftype='text-single',
                           label='Name',
                           value=title,
                           required=True)
            # NOTE This does not look good in Gajim
            # url = form.add_field(ftype='fixed',
            #                      label=url)
            #url['validate']['datatype'] = 'xs:anyURI'
            options = form.add_field(var='url',
                                     ftype='list-single',
                                     label='URL',
                                     value=url)
            options.addOption(url, url)
            feed_id_str = str(feed_id)
            options = form.add_field(var='id',
                                     ftype='list-single',
                                     label='ID #',
                                     value=feed_id_str)
            options.addOption(feed_id_str, feed_id_str)
            form.add_field(desc='Comma-separated tags.',
                           ftype='text-single',
                           label='Tags',
                           value=tags,
                           var='tags_new')
            form.add_field(ftype='hidden',
                           value=tags,
                           var='tags_old')
        form.add_field(ftype='fixed',
                       label='Options')
        options = form.add_field(ftype='list-single',
                                 label='Priority',
                                 value='0',
                                 var='priority')
        options['validate']['datatype'] = 'xs:integer'
        options['validate']['range'] = { 'minimum': 1, 'maximum': 5 }
        i = 0
        while i <= 5:
            num = str(i)
            options.addOption(num, num)
            i += 1
        form.add_field(ftype='boolean',
                       label='Enabled',
                       value=True,
                       var='enabled')
        session['allow_complete'] = True
        # session['allow_prev'] = True
        session['cancel'] = self._handle_cancel
        session['has_next'] = False
        session['next'] = self._handle_subscription_complete
        session['payload'] = form
        return session


    # TODO Create a new form. Do not "recycle" the last form.
    async def _handle_subscription_complete(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = session['from'].bare
        values = payload['values']
        if is_operator(self, jid_bare) and 'jid' in values:
            jid_bare = values['jid'][0]
        db_file = config.get_pathname_to_database(jid_bare)
        # url = values['url']
        # feed_id = sqlite.get_feed_id(db_file, url)
        # feed_id = feed_id[0]
        # if feed_id: feed_id = feed_id[0]
        feed_id = values['id']
        enabled = values['enabled']
        # if enabled:
        #     enabled_status = 1
        # else:
        #     enabled_status = 0
        #     await sqlite.mark_feed_as_read(db_file, feed_id)
        enabled_status = 1 if enabled else 0
        if not enabled_status: await sqlite.mark_feed_as_read(db_file, feed_id)
        await sqlite.set_enabled_status(db_file, feed_id, enabled_status)
        name = values['name']
        await sqlite.set_feed_title(db_file, feed_id, name)
        priority = values['priority']
        tags_new = values['tags_new']
        tags_old = values['tags_old']
        # Add new tags
        for tag in tags_new.split(','):
            tag = tag.strip()
            if not tag:
                continue
            tag = tag.lower()
            tag_id = sqlite.get_tag_id(db_file, tag)
            if not tag_id:
                await sqlite.set_new_tag(db_file, tag)
                tag_id = sqlite.get_tag_id(db_file, tag)
            tag_id = tag_id[0]
            if not sqlite.is_tag_id_of_feed_id(db_file, tag_id, feed_id):
                await sqlite.set_feed_id_and_tag_id(db_file, feed_id, tag_id)
        # Remove tags that were not submitted
        for tag in tags_old[0].split(','):
            tag = tag.strip()
            if not tag:
                continue
            if tag not in tags_new:
                tag_id = sqlite.get_tag_id(db_file, tag)
                tag_id = tag_id[0]
                await sqlite.delete_feed_id_tag_id(db_file, feed_id, tag_id)
                sqlite.is_tag_id_associated(db_file, tag_id)
                await sqlite.delete_tag_by_index(db_file, tag_id)
        # form = self['xep_0004'].make_form('form', 'Subscription')
        # form['instructions'] = ('📁️ Subscription #{} has been {}'
        #                         .format(feed_id, action))
        form = payload
        form['title'] = 'Done'
        form['instructions'] = ('has been completed!')
        # session["has_next"] = False
        session['next'] = None
        session['payload'] = form
        # session['type'] = 'submit'
        return session


    async def _handle_advanced(self, iq, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = session['from'].bare
        chat_type = await XmppUtilities.get_chat_type(self, jid_bare)
        if is_access(self, jid_bare, jid_full, chat_type):
            form = self['xep_0004'].make_form('form', 'Advanced')
            form['instructions'] = 'Extended options'
            options = form.add_field(ftype='list-single',
                                     label='Choose',
                                     required=True,
                                     var='option')
            if is_operator(self, jid_bare):
                options.addOption('Administration', 'admin')
            # options.addOption('Activity', 'activity')
            # options.addOption('Filters', 'filter')
            # options.addOption('Statistics', 'statistics')
            # options.addOption('Scheduler', 'scheduler')
            options.addOption('Import', 'import')
            options.addOption('Export', 'export')
            session['allow_prev'] = False
            session['payload'] = form
            session['has_next'] = True
            session['next'] = self._handle_advanced_result
            session['prev'] = self._handle_advanced
        else:
            if not is_operator(self, jid_bare):
                text_warn = 'This resource is restricted to operators.'
            elif chat_type == 'groupchat':
                text_warn = ('This resource is restricted to moderators of {}.'
                             .format(jid_bare))
            elif chat_type == 'error':
                text_warn = ('Could not determine chat type of {}.'
                             .format(jid_bare))
            else:
                text_warn = 'This resource is forbidden.'
            session['notes'] = [['warn', text_warn]]
        return session


    async def _handle_advanced_result(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = session['from'].bare
        match payload['values']['option']:
            case 'activity':
                # TODO dialog for JID and special dialog for operator
                # Here you can monitor activity
                text_note = 'This feature is not yet available.'
                session['notes'] = [['info', text_note]]
            case 'admin':
                # NOTE Even though this check is already conducted on previous
                # form, this check is being done just in case.
                if is_operator(self, jid_bare):
                    if self.is_component:
                        # NOTE This will be changed with XEP-0222 XEP-0223
                        text_info = ('Subscriber management options are '
                                     'currently not available for Slixfeed '
                                     'running as component. Once support for '
                                     'XEP-0222 and XEP-0223 be added, this '
                                     'panel will be usable for components as '
                                     'well.')
                        session['has_next'] = False
                        session['next'] = None
                        session['notes'] = [['info', text_info]]
                    else:
                        form = self['xep_0004'].make_form('form', 'Admin Panel')
                        form['instructions'] = ('Choose the type of prospect '
                                                'you want to handle with')
                        options = form.add_field(desc='Select a prospect type',
                                                 ftype='list-single',
                                                 label='Manage',
                                                 required=True,
                                                 value='subscribers',
                                                 var='action')
                        options.addOption('Bookmarks', 'bookmarks')
                        options.addOption('Contacts', 'roster')
                        options.addOption('Nodes', 'nodes')
                        options.addOption('PubSub', 'pubsub')
                        options.addOption('Subscribers', 'subscribers')
                        session['payload'] = form
                        session['next'] = self._handle_admin_action
                        session['has_next'] = True
                else:
                    logger.warning('An unauthorized attempt to access '
                                   'bookmarks has been detected for JID {} at '
                                   '{}'.format(jid_bare, dt.timestamp()))
                    text_warn = 'This resource is restricted.'
                    session['notes'] = [['warn', text_warn]]
                    session['has_next'] = False
                    session['next'] = None
            # case 'filters':
                # TODO Ability to edit lists.toml or filters.toml
            case 'scheduler':
                # TODO Set days and hours to receive news
                text_note = 'This feature is not yet available.'
                session['notes'] = [['info', text_note]]
                session['has_next'] = False
                session['next'] = None
            case 'statistics':
                # TODO Here you can monitor statistics
                text_note = 'This feature is not yet available.'
                session['notes'] = [['info', text_note]]
                session['has_next'] = False
                session['next'] = None
            case 'import':
                form = self['xep_0004'].make_form('form', 'Import')
                form['instructions'] = 'Importing feeds'
                url = form.add_field(desc='Enter URL to an OPML file.',
                                     ftype='text-single',
                                     label='URL',
                                     required=True,
                                     var='url')
                url['validate']['datatype'] = 'xs:anyURI'
                if is_operator(self, jid_bare):
                    form.add_field(ftype='fixed',
                                    label='* Operators',
                                    desc='This section allows you to import '
                                    'subscriptions for any subscriber.')
                    form.add_field(desc='Enter a Jabber ID to import '
                                   'subscriptions to (The default Jabber ID '
                                   'is your own).',
                                   ftype='text-single',
                                   label='Jabber ID',
                                   var='jid')
                session['allow_complete'] = True
                session['has_next'] = False
                session['next'] = self._handle_import_complete
                session['payload'] = form
            case 'export':
                form = self['xep_0004'].make_form('form', 'Export')
                form['instructions'] = ('It is always recommended to export '
                                        'subscriptions into OPML file, in '
                                        'order to easily import subscriptions '
                                        'from one Feed Reader to another. See '
                                        'About -> News Software for a list of '
                                        'Feed Readers offered for desktop and '
                                        'mobile devices.')
                options = form.add_field(desc='Choose export format.',
                                         ftype='list-multi',
                                         label='Format',
                                         required=True,
                                         value='opml',
                                         var='filetype')
                options.addOption('Markdown', 'md')
                options.addOption('OPML', 'opml')
                # options.addOption('HTML', 'html')
                # options.addOption('XBEL', 'xbel')
                if is_operator(self, jid_bare):
                    # form['instructions'] = ('Special section for operators:\n'
                    #                         'This section allows you to '
                    #                         'import and export subscriptions '
                    #                         'for a JID of your choice.')
                    form.add_field(ftype='fixed',
                                    label='* Operators',
                                    desc='This section allows you to export '
                                    'subscriptions of any subscriber.')
                    options = form.add_field(desc='Select a Jabber ID to '
                                             'export subscriptions from.',
                                             ftype='list-single',
                                             label='Subscriber',
                                             value=jid_bare,
                                             var='jid')
                    # options.addOption(self.boundjid.bare, self.boundjid.bare)
                    jids = []
                    contacts = await XmppRoster.get_contacts(self)
                    for contact in contacts:
                        jids.extend([contact])
                    conferences = await XmppBookmark.get_bookmarks(self)
                    for conference in conferences:
                        jids.extend([conference['jid']])
                    pubsubs = await XmppPubsub.get_pubsub_services(self)
                    for pubsub in pubsubs:
                        jids.extend([pubsub['jid']])
                    for jid_bare in sorted(jids):
                        options.addOption(jid_bare, jid_bare)
                session['allow_complete'] = True
                session['has_next'] = False
                session['next'] = self._handle_export_complete
                session['payload'] = form
        # session['allow_prev'] = True
        # session['prev'] = self._handle_advanced
        return session


    async def _handle_about(self, iq, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        form = self['xep_0004'].make_form('form', 'About')
        form['instructions'] = 'Information about Slixfeed and related projects'
        options = form.add_field(var='option',
                                 ftype='list-single',
                                 label='About',
                                 required=True,
                                 value='about')
        config_dir = config.get_default_config_directory()
        with open(config_dir + '/' + 'about.toml', mode="rb") as information:
            entries = tomllib.load(information)
        for entry in entries:
            label = entries[entry][0]['title']
            options.addOption(label, entry)
            # options.addOption('Tips', 'tips')
        session['payload'] = form
        session['next'] = self._handle_about_result
        session['has_next'] = True
        return session


    async def _handle_about_result(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        config_dir = config.get_default_config_directory()
        with open(config_dir + '/' + 'about.toml', mode="rb") as information:
            entries = tomllib.load(information)
        entry_key = payload['values']['option']
            # case 'terms':
            #     title = 'Policies'
            #     subtitle = 'Terms and Conditions'
            #     content = action.manual('information.toml', 'terms')
            # case 'tips':
            #     # Tips and tricks you might have not known about Slixfeed and XMPP!
            #     title = 'Help'
            #     subtitle = 'Tips & Tricks'
            #     content = 'This page is not yet available.'
            # case 'translators':
            #     title = 'Translators'
            #     subtitle = 'From all across the world'
            #     content = action.manual('information.toml', 'translators')
        # title = entry_key.capitalize()
        # form = self['xep_0004'].make_form('result', title)
        for entry in entries[entry_key]:
            if 'title' in entry:
                title = entry['title']
                form = self['xep_0004'].make_form('result', title)
                subtitle = entry['subtitle']
                form['instructions'] = subtitle
                continue
            for e_key in entry:
                e_val = entry[e_key]
                e_key = e_key.capitalize()
                # form.add_field(ftype='fixed',
                #                label=e_val)
                if e_key == 'Name':
                    desc = entry['desc'] if 'desc' in entry and entry['desc'] else None
                    form.add_field(ftype='fixed',
                                   label=e_val,
                                   desc=desc)
                    continue
                if e_key == 'Desc':
                    continue
                if isinstance(e_val, list):
                    form_type = 'text-multi'
                else:
                    form_type = 'text-single'
                form.add_field(label=e_key,
                               ftype=form_type,
                               value=e_val)
        # Gajim displays all form['instructions'] on top
        # Psi ignore the latter form['instructions']
        # form['instructions'] = 'YOU!\n🫵️\n- Join us -'
        session['payload'] = form
        session['allow_complete'] = True
        session['allow_prev'] = True
        session["has_next"] = False
        session['next'] = None
        # session['payload'] = None # Crash Cheogram
        session['prev'] = self._handle_about
        return session


    async def _handle_motd(self, iq, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        # TODO add functionality to attach image.
        # Here you can add groupchat rules,post schedule, tasks or
        # anything elaborated you might deem fit. Good luck!
        text_note = 'This feature is not yet available.'
        session['notes'] = [['info', text_note]]
        return session


    async def _handle_help(self, iq, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))

        config_dir = config.get_default_config_directory()
        with open(config_dir + '/' + 'commands.toml', mode="rb") as commands:
            cmds = tomllib.load(commands)

        form = self['xep_0004'].make_form('result', 'Manual')
        form['instructions'] = 'Help manual for interactive chat'

        # text = '🛟️ Help and Information about Slixfeed\n\n'
        # for cmd in cmds:
        #     name = cmd.capitalize()
        #     elements = cmds[cmd]
        #     text += name + '\n'
        #     for key, value in elements.items():
        #         text += " " + key.capitalize() + '\n'
        #         for line in value.split("\n"):
        #             text += "  " + line + '\n'
        # form['instructions'] = text

        for cmd in cmds:
            name = cmd.capitalize()
            form.add_field(var='title',
                           ftype='fixed',
                           label=name)
            elements = cmds[cmd]
            for key, value in elements.items():
                key = key.replace('_', ' ')
                key = key.capitalize()
                form.add_field(var='title',
                               ftype='text-multi',
                               label=key,
                               value=value)
        session['payload'] = form
        return session


    async def _handle_import_complete(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        form = payload
        values = payload['values']
        url = values['url']
        if url.startswith('http') and url.endswith('.opml'):
            jid_bare = session['from'].bare
            if is_operator(self, jid_bare) and 'jid' in values:
                jid = values['jid']
                jid_bare = jid[0] if isinstance(jid, list) else jid
            db_file = config.get_pathname_to_database(jid_bare)
            result = await fetch.http(url)
            count = await Opml.import_from_file(db_file, result)
            try:
                int(count)
                # form = self['xep_0004'].make_form('result', 'Done')
                # form['instructions'] = ('✅️ Feeds have been imported')
                form['title'] = 'Done'
                form['instructions'] = ('has been completed!')
                message = '{} feeds have been imported.'.format(count)
                form.add_field(var='Message',
                               ftype='text-single',
                               value=message)
                session['payload'] = form
            except:
                session['payload'] = None
                text_error = ('Import failed. Filetype does not appear to be '
                              'an OPML file.')
                session['notes'] = [['error', text_error]]
        else:
            session['payload'] = None
            text_error = 'Import aborted. Send URL of OPML file.'
            session['notes'] = [['error', text_error]]
        session["has_next"] = False
        session['next'] = None
        return session


    async def _handle_export_complete(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        form = self['xep_0004'].make_form('result', 'Done')
        form['instructions'] = 'Export has been completed successfully!'
        # form['type'] = 'result'
        values = payload['values']
        jid_bare = session['from'].bare
        if is_operator(self, jid_bare) and 'jid' in values:
            jid = values['jid']
            jid_bare = jid[0] if isinstance(jid, list) else jid
        # form = self['xep_0004'].make_form('result', 'Done')
        # form['instructions'] = ('✅️ Feeds have been exported')
        exts = values['filetype']
        for ext in exts:
            filename = Feed.export_feeds(jid_bare, ext)
            url = await XmppUpload.start(self, jid_bare, filename)
            chat_type = await XmppUtilities.get_chat_type(self, jid_bare)
            XmppMessage.send_oob(self, jid_bare, url, chat_type)
            url_field = form.add_field(var=ext.upper(),
                                       ftype='text-single',
                                       label=ext,
                                       value=url)
            url_field['validate']['datatype'] = 'xs:anyURI'
        session["has_next"] = False
        session['next'] = None
        session['payload'] = form
        return session


    # TODO Exclude feeds that are already in database or requester.
    # TODO Attempt to look up for feeds of hostname of JID (i.e. scan
    # jabber.de for feeds for juliet@jabber.de)
    async def _handle_promoted(self, iq, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = session['from'].bare
        jid_full = str(session['from'])
        chat_type = await XmppUtilities.get_chat_type(self, jid_bare)
        if is_access(self, jid_bare, jid_full, chat_type):
            form = self['xep_0004'].make_form('form', 'Subscribe')
            # NOTE Refresh button would be of use
            form['instructions'] = 'Featured subscriptions'
            url = Utilities.pick_a_feed()
            # options = form.add_field(desc='Click to subscribe.',
            #                          ftype="boolean",
            #                          label='Subscribe to {}?'.format(url['name']),
            #                          var='choice')
            # form.add_field(var='subscription',
            #                 ftype='hidden',
            #                 value=url['link'])
            options = form.add_field(desc='Click to subscribe.',
                                     ftype="list-single",
                                     label='Subscribe',
                                     var='subscription')
            for i in range(10):
                url = Utilities.pick_a_feed()
                options.addOption(url['name'], url['link'])
            # jid_bare = session['from'].bare
            if '@' in jid_bare:
                hostname = jid_bare.split('@')[1]
                url = 'http://' + hostname
            result = await crawl.probe_page(url)
            if not result:
                url = {'url' : url,
                        'index' : None,
                        'name' : None,
                        'code' : None,
                        'error' : True,
                        'exist' : False}
            elif isinstance(result, list):
                for url in result:
                    if url['link']: options.addOption('{}\n{}'.format(url['name'], url['link']), url['link'])
            else:
                url = result
                # Automatically set priority to 5 (highest)
                if url['link']: options.addOption(url['name'], url['link'])
            session['allow_complete'] = False
            session['allow_prev'] = True
            # singpolyma: Don't use complete action if there may be more steps
            # https://gitgud.io/sjehuda/slixfeed/-/merge_requests/13
            # Gajim: On next form Gajim offers no button other than "Commands".
            # Psi: Psi closes the dialog.
            # Conclusion, change session['has_next'] from False to True
            # session['has_next'] = False
            session['has_next'] = True
            session['next'] = self._handle_subscription_new
            session['payload'] = form
            session['prev'] = self._handle_promoted
        else:
            if not is_operator(self, jid_bare):
                text_warn = 'This resource is restricted to operators.'
            elif chat_type == 'groupchat':
                text_warn = ('This resource is restricted to moderators of {}.'
                             .format(jid_bare))
            elif chat_type == 'error':
                text_warn = ('Could not determine chat type of {}.'
                             .format(jid_bare))
            else:
                text_warn = 'This resource is forbidden.'
            session['notes'] = [['warn', text_warn]]
        return session


    async def _handle_admin_action(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        match payload['values']['action']:
            case 'bookmarks':
                form = self['xep_0004'].make_form('form', 'Bookmarks')
                form['instructions'] = 'Managing bookmarks'
                options = form.add_field(desc='Select a bookmark to edit.',
                                         ftype='list-single',
                                         label='Jabber ID',
                                         required=True,
                                         var='jid')
                conferences = await XmppBookmark.get_bookmarks(self)
                for conference in conferences:
                    options.addOption(conference['name'], conference['jid'])
                session['has_next'] = True
                session['next'] = self._handle_bookmarks_edit
            case 'roster':
                form = self['xep_0004'].make_form('form', 'Contacts')
                form['instructions'] = 'Organizing contacts'
                options = form.add_field(desc='Select a contact.',
                                         ftype='list-single',
                                         label='Contact',
                                         required=True,
                                         var='jid')
                contacts = await XmppRoster.get_contacts(self)
                for contact in contacts:
                    contact_name = contacts[contact]['name']
                    contact_name = contact_name if contact_name else contact
                    options.addOption(contact_name, contact)
                options = form.add_field(ftype='list-single',
                                         label='Action',
                                         required=True,
                                         var='action')
                options.addOption('Display', 'view')
                options.addOption('Edit', 'edit')
                session['has_next'] = True
                session['next'] = self._handle_contact_action
            case 'subscribers':
                form = self['xep_0004'].make_form('form', 'Subscribers')
                form['instructions'] = 'Committing subscriber action'
                options = form.add_field(ftype='list-single',
                                         label='Action',
                                         required=True,
                                         value='message',
                                         var='action')
                options.addOption('Request authorization From', 'from')
                options.addOption('Resend authorization To', 'to')
                options.addOption('Send message', 'message')
                options.addOption('Remove', 'remove')
                options = form.add_field(desc='Select a contact.',
                                         ftype='list-single',
                                         label='Jabber ID',
                                         required=True,
                                         var='jid')
                contacts = await XmppRoster.get_contacts(self)
                for contact in contacts:
                    contact_name = contacts[contact]['name']
                    contact_name = contact_name if contact_name else contact
                    options.addOption(contact_name, contact)
                form.add_field(var='subject',
                               ftype='text-single',
                               label='Subject')
                form.add_field(desc='Add a descriptive message.',
                               ftype='text-multi',
                               label='Message',
                               var='message')
                session['allow_complete'] = True
                session['has_next'] = False
                session['next'] = self._handle_subscribers_complete
            case 'nodes':
                form = self['xep_0004'].make_form('form', 'PubSub')
                form['instructions'] = ('Select a Publish-Subscribe service '
                                        'of which nodes you want to list.')
                # jid_bare = self.boundjid.bare
                # enabled_state = Config.get_setting_value(self.settings, jid_bare, 'enabled')

                results = await XmppPubsub.get_pubsub_services(self)
                options = form.add_field(desc='Select a PubSub service.',
                                         ftype='list-single',
                                         label='Jabber ID',
                                         value=self.boundjid.bare,
                                         var='jid')
                for result in results + [{'jid' : self.boundjid.bare,
                                           'name' : self.alias}]:
                    name = result['name']
                    jid_bare = result['jid']
                    options.addOption(name, jid_bare)
                session['has_next'] = True
                session['next'] = self._handle_nodes
            case 'pubsub':
                form = self['xep_0004'].make_form('form', 'PubSub')
                form['instructions'] = ('Designate Publish-Subscribe services '
                                        'for IoT updates, news publishing, '
                                        'and even for microblogging on '
                                        'platforms such as Libervia and Movim.')
                form.add_field(desc='Select PubSub services to designate.',
                               ftype='fixed',
                               label='Jabber ID')
                # jid_bare = self.boundjid.bare
                # enabled_state = Config.get_setting_value(self.settings, jid_bare, 'enabled')

                results = await XmppPubsub.get_pubsub_services(self)
                for result in results + [{'jid' : self.boundjid.bare,
                                           'name' : self.alias}]:
                    jid_bare = result['jid']
                    name = result['name']
                    enabled_state = Config.get_setting_value(
                        self.settings, jid_bare, 'enabled')
                    form.add_field(desc=jid_bare,
                                   ftype='boolean',
                                   label=name,
                                   value=enabled_state,
                                   var=jid_bare)
                session['allow_complete'] = True
                session['has_next'] = False
                session['next'] = self._handle_pubsub_complete
        # session['allow_prev'] = True
        session['payload'] = form
        # session['prev'] = self._handle_advanced
        return session


    def _handle_nodes(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        values = payload['values']
        jid = values['jid']
        form = self['xep_0004'].make_form('form', 'PubSub')
        options = form.add_field(desc='Select a desired action.',
                                 ftype='list-single',
                                 label='Action',
                                 value='browse',
                                 var='action')
        options.addOption('Browse', 'browse')
        # options.addOption('Edit', 'edit')
        options.addOption('Purge', 'purge')
        options.addOption('Delete', 'delete')
        form.add_field(var='jid',
                       ftype='hidden',
                       value=jid)
        session['has_next'] = True
        session['next'] = self._handle_nodes_action
        session['allow_prev'] = True
        session['payload'] = form
        session['prev'] = self._handle_advanced
        return session


    async def _handle_nodes_action(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        values = payload['values']
        action = values['action']
        jid = values['jid'][0]
        form = self['xep_0004'].make_form('form', 'PubSub')
        match action:
            case 'browse':
                session['has_next'] = False
                session['next'] = self._handle_node_browse
                form['instructions'] = 'Browsing nodes'
                options = form.add_field(desc='Select a node to view.',
                                         ftype='list-single',
                                         label='Nodes',
                                         var='node')
            case 'delete':
                session['allow_complete'] = True
                session['has_next'] = False
                session['next'] = self._handle_nodes_delete
                form['instructions'] = 'Deleting nodes'
                options = form.add_field(desc='Select nodes to delete.',
                                         ftype='list-multi',
                                         label='Nodes',
                                         var='nodes')
            case 'edit':
                # session['allow_complete'] = False
                session['has_next'] = False
                session['next'] = self._handle_node_edit
                form['instructions'] = 'Editing nodes'
                options = form.add_field(desc='Select a node to edit.',
                                         ftype='list-single',
                                         label='Nodes',
                                         var='node')
            case 'purge':
                session['allow_complete'] = True
                session['has_next'] = False
                session['next'] = self._handle_nodes_purge
                form['instructions'] = 'Purging nodes'
                options = form.add_field(desc='Select nodes to purge.',
                                         ftype='list-multi',
                                         label='Nodes',
                                         var='nodes')
        iq = await XmppPubsub.get_nodes(self, jid)
        nodes = iq['disco_items']
        for node in nodes:
            node_id = node['node']
            node_name = node['name']
            options.addOption(node_name, node_id)
        form.add_field(var='jid',
                       ftype='hidden',
                       value=jid)
        session['allow_prev'] = True
        session['payload'] = form
        return session


    async def _handle_node_browse(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        values = payload['values']
        jid = values['jid'][0]
        node = values['node']
        form = self['xep_0004'].make_form('form', 'PubSub')
        form['instructions'] = 'Browsing node items'
        options = form.add_field(desc='Select an item to view.',
                                 ftype='list-single',
                                 label='Items',
                                 var='item_id')
        iq = await XmppPubsub.get_items(self, jid, node)
        items = iq['pubsub']['items']
        for item in items:
            item_id = item['id']
            item_name = item_id
            options.addOption(item_name, item_id)
        form.add_field(var='jid',
                       ftype='hidden',
                       value=jid)
        form.add_field(var='node',
                       ftype='hidden',
                       value=node)
        session['next'] = self._handle_item_view
        session['payload'] = form
        return session


    async def _handle_item_view(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        values = payload['values']
        item_id = values['item_id']
        jid = values['jid'][0]
        node = values['node'][0]
        iq = await XmppPubsub.get_item(self, jid, node, item_id)
        form = self['xep_0004'].make_form('form', 'PubSub')
        # for item in iq['pubsub']['items']['substanzas']:
        # for item in iq['pubsub']['items']:
        #     item['payload']
        
        content = ''
        # TODO Check whether element of type Atom
        # NOTE Consider pubsub#type of XEP-0462: PubSub Type Filtering
        atom_entry = iq['pubsub']['items']['item']['payload']
        for element in atom_entry:
            if element.text:
                content += element.text + '\n\n'
                # content += Html.remove_html_tags(element.text) + '\n\n'
            if element.attrib:
                for i in element.attrib:
                    content += element.attrib[i] + '\n\n'
            # if element.text: content += element.text + '\n\n'
        
        form.add_field(ftype="text-multi",
                       label='Content',
                       value=content)
        session['allow_prev'] = True
        session['payload'] = form
        return session

    # FIXME Undefined name 'jid_bare'
    async def _handle_node_edit(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        values = payload['values']
        jid = values['jid'][0]
        node = values['node']
        properties = await XmppPubsub.get_node_properties(self, jid, node)
        form = self['xep_0004'].make_form('form', 'PubSub')
        form['instructions'] = 'Editing bookmark'
        jid_split = properties['jid'].split('@')
        room = jid_split[0]
        host = jid_split[1]
        options = form.addField(var='jid',
                                ftype='list-single',
                                label='Jabber ID',
                                value=jid_bare)
        options.addOption(jid_bare, jid_bare)
        form.addField(var='alias',
                      ftype='text-single',
                      label='Alias',
                      value=properties['nick'],
                      required=True)
        form.addField(var='name',
                      ftype='text-single',
                      label='Name',
                      value=properties['name'],
                      required=True)
        form.addField(var='room',
                      ftype='text-single',
                      label='Room',
                      value=room,
                      required=True)
        form.addField(var='host',
                      ftype='text-single',
                      label='Host',
                      value=host,
                      required=True)
        form.addField(var='password',
                      ftype='text-private',
                      label='Password',
                      value=properties['password'])
        form.addField(var='language',
                      ftype='text-single',
                      label='Language',
                      value=properties['lang'])
        form.add_field(var='autojoin',
                       ftype='boolean',
                       label='Auto-join',
                       value=properties['autojoin'])


    async def _handle_nodes_purge(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        values = payload['values']
        jid = values['jid'][0]
        nodes = values['nodes']
        for node in nodes:
            XmppPubsub.purge_node(self, jid, node)
        form = payload
        form['title'] = 'Done'
        session['next'] = None
        session['notes'] = [['info', 'Nodes have been purged!']]
        session['payload'] = form
        return session


    async def _handle_nodes_delete(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        values = payload['values']
        jid = values['jid'][0]
        nodes = values['nodes']
        for node in nodes:
            XmppPubsub.delete_node(self, jid, node)
        form = payload
        form['title'] = 'Done'
        session['next'] = None
        session['notes'] = [['info', 'Nodes have been deleted!']]
        session['payload'] = form
        return session


    async def _handle_pubsub_complete(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        values = payload['values']
        print(self.settings)
        for key in values:
            if key:
                jid_bare = key
                value = values[key]
                db_file = config.get_pathname_to_database(jid_bare)
                if jid_bare not in self.settings:
                    Config.add_settings_jid(self.settings, jid_bare, db_file)
                await Config.set_setting_value(self.settings, jid_bare,
                                               db_file, 'enabled', value)
        print(self.settings)
        text_note = 'Done.'
        session['has_next'] = False
        session['next'] = None
        session['notes'] = [['info', text_note]]
        session['payload'] = None
        return session


    async def _handle_subscribers_complete(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        values = payload['values']
        jid_bare = values['jid']
        value_subject = values['subject']
        message_subject = value_subject if value_subject else None
        value_message = values['message']
        message_body = value_message if value_message else None
        match values['action']:
            case 'from':
                XmppPresence.subscription(self, jid_bare, 'subscribe')
                if not message_subject:
                    message_subject = 'System Message'
                if not message_body:
                    message_body = ('This user wants to subscribe to your '
                                    'presence. Click the button labelled '
                                    '"Add/Auth" toauthorize the subscription. '
                                    'This will also add the person to your '
                                    'contact list if it is not already there.')
            case 'remove':
                XmppRoster.remove(self, jid_bare)
                if not message_subject:
                    message_subject = 'System Message'
                if not message_body:
                    message_body = 'Your authorization has been removed!'
            case 'to':
                XmppPresence.subscription(self, jid_bare, 'subscribed')
                if not message_subject:
                    message_subject = 'System Message'
                if not message_body:
                    message_body = 'Your authorization has been approved!'
        if message_subject:
            XmppMessage.send_headline(self, jid_bare, message_subject,
                                      message_body, 'chat')
        elif message_body:
            XmppMessage.send(self, jid_bare, message_body, 'chat')
        form = payload
        form['title'] = 'Done'
        form['instructions'] = ('has been completed!')
        # session["has_next"] = False
        session['next'] = None
        session['payload'] = form
        return session


    async def _handle_contact_action(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        values = payload['values']
        jid_bare = values['jid']
        form = self['xep_0004'].make_form('form', 'Contacts')
        session['allow_complete'] = True
        roster = await XmppRoster.get_contacts(self)
        properties = roster[jid_bare]
        match values['action']:
            case 'edit':
                form['instructions'] = 'Editing contact'
                options = form.add_field(var='jid',
                                         ftype='list-single',
                                         label='Jabber ID',
                                         value=jid_bare)
                options.addOption(jid_bare, jid_bare)
                form.add_field(var='name',
                               ftype='text-single',
                               label='Name',
                               value=properties['name'])
                session['allow_complete'] = True
                session['next'] = self._handle_contacts_complete
            case 'view':
                form['instructions'] = 'Viewing contact'
                contact_name = properties['name']
                contact_name = contact_name if contact_name else jid_bare
                form.add_field(var='name',
                               ftype='text-single',
                               label='Name',
                               value=properties['name'])
                form.add_field(var='from',
                               ftype='boolean',
                               label='From',
                               value=properties['from'])
                form.add_field(var='to',
                               ftype='boolean',
                               label='To',
                               value=properties['to'])
                form.add_field(var='pending_in',
                               ftype='boolean',
                               label='Pending in',
                               value=properties['pending_in'])
                form.add_field(var='pending_out',
                               ftype='boolean',
                               label='Pending out',
                               value=properties['pending_out'])
                form.add_field(var='whitelisted',
                               ftype='boolean',
                               label='Whitelisted',
                               value=properties['whitelisted'])
                form.add_field(var='subscription',
                               ftype='fixed',
                               label='Subscription',
                               value=properties['subscription'])
                session['allow_complete'] = None
                session['next'] = None
        # session['allow_complete'] = True
        session['allow_prev'] = True
        session['has_next'] = False
        # session['next'] = None
        session['payload'] = form
        session['prev'] = self._handle_contacts_complete
        return session


    def _handle_contacts_complete(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        values = payload['values']
        jid_bare = values['jid']
        name = values['name']
        name_old = XmppRoster.get_contact_name(self, jid_bare)
        if name == name_old:
            message = ('No action has been taken.  Reason: New '
                       'name is identical to the current one.')
            session['payload'] = None
            session['notes'] = [['info', message]]
        else:
            XmppRoster.set_contact_name(self, jid_bare, name)
            form = payload
            form['title'] = 'Done'
            form['instructions'] = ('has been completed!')
            session['payload'] = form
        session['next'] = None
        return session


    async def _handle_bookmarks_edit(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = payload['values']['jid']
        properties = await XmppBookmark.get_bookmark_properties(self, jid_bare)
        form = self['xep_0004'].make_form('form', 'Bookmarks')
        form['instructions'] = 'Editing bookmark'
        jid_split = properties['jid'].split('@')
        room = jid_split[0]
        host = jid_split[1]
        options = form.addField(var='jid',
                                ftype='list-single',
                                label='Jabber ID',
                                value=jid_bare)
        options.addOption(jid_bare, jid_bare)
        form.addField(var='alias',
                      ftype='text-single',
                      label='Alias',
                      value=properties['nick'],
                      required=True)
        form.addField(var='name',
                      ftype='text-single',
                      label='Name',
                      value=properties['name'],
                      required=True)
        form.addField(var='room',
                      ftype='text-single',
                      label='Room',
                      value=room,
                      required=True)
        form.addField(var='host',
                      ftype='text-single',
                      label='Host',
                      value=host,
                      required=True)
        form.addField(var='password',
                      ftype='text-private',
                      label='Password',
                      value=properties['password'])
        form.addField(var='language',
                      ftype='text-single',
                      label='Language',
                      value=properties['lang'])
        form.add_field(var='autojoin',
                       ftype='boolean',
                       label='Auto-join',
                       value=properties['autojoin'])
        # options = form.add_field(var='action',
        #                ftype='list-single',
        #                label='Action',
        #                value='join')
        # options.addOption('Add', 'add')
        # options.addOption('Join', 'join')
        # options.addOption('Remove', 'remove')
        session['allow_complete'] = True
        # session['allow_prev'] = True
        session['has_next'] = False
        session['next'] = self._handle_bookmarks_complete
        session['payload'] = form
        # session['prev'] = self._handle_admin_action # FIXME (1) Not realized (2) Should be _handle_advanced
        return session


    async def _handle_bookmarks_complete(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        form = self['xep_0004'].make_form('result', 'Done')
        form['instructions'] = ('Bookmark has been saved')
        values = payload['values']
        await XmppBookmark.add(self, properties=values)
        for i in values:
            key = str(i)
            val = str(values[i])
            if val and key == 'password': val = '**********'
            # if not val: val = 'None'
            # form_type = 'text-single' if key != 'password' else 'text-private'
            if val:
                form.add_field(var=key,
                                ftype='text-single',
                                label=key.capitalize(),
                                value=val)
        session['next'] = None
        session['payload'] = form
        # session['notes'] = [['warn', text_warn]]
        return session


    async def _handle_settings(self, iq, session):
        """
        Respond to the initial request for a command.
    
        Arguments:
            iq      -- The iq stanza containing the command request.
            session -- A dictionary of data relevant to the command
                       session. Additional, custom data may be saved
                       here to persist across handler callbacks.
        """
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = session['from'].bare
        chat_type = await XmppUtilities.get_chat_type(self, jid_bare)
        if is_access(self, jid_bare, jid_full, chat_type):
            db_file = config.get_pathname_to_database(jid_bare)
            if jid_bare not in self.settings:
                Config.add_settings_jid(self.settings, jid_bare, db_file)
            form = self['xep_0004'].make_form('form', 'Settings')
            form['instructions'] = 'Editing settings of {}'.format(jid_bare)
            value = Config.get_setting_value(self.settings, jid_bare, 'enabled')
            value = str(value)
            value = int(value)
            if value:
                value = True
            else:
                value = False
            form.add_field(desc='Enable news updates.',
                           ftype='boolean',
                           label='Enabled',
                           value=value,
                           var='enabled')
            value = Config.get_setting_value(self.settings, jid_bare, 'media')
            value = str(value)
            value = int(value)
            if value:
                value = True
            else:
                value = False
            form.add_field(desc='Send audio, images or videos if found.',
                           ftype='boolean',
                           label='Display media',
                           value=value,
                           var='media')
            value = Config.get_setting_value(self.settings, jid_bare, 'old')
            value = str(value)
            value = int(value)
            if value:
                value = True
            else:
                value = False
            form.add_field(desc='Treat all items of newly added subscriptions '
                           'as new.',
                           ftype='boolean',
                           # label='Send only new items',
                           label='Include old news',
                           value=value,
                           var='old')
            value = Config.get_setting_value(self.settings, jid_bare, 'interval')
            value = str(value)
            value = int(value)
            value = value/60
            value = int(value)
            value = str(value)
            options = form.add_field(desc='Interval update (in hours).',
                                     ftype='list-single',
                                     label='Interval',
                                     value=value,
                                     var='interval')
            options['validate']['datatype'] = 'xs:integer'
            options['validate']['range'] = { 'minimum': 1, 'maximum': 48 }
            i = 1
            while i <= 48:
                x = str(i)
                options.addOption(x, x)
                if i >= 12:
                    i += 6
                else:
                    i += 1
            value = Config.get_setting_value(self.settings, jid_bare, 'quantum')
            value = str(value)
            options = form.add_field(desc='Amount of items per update.',
                                     ftype='list-single',
                                     label='Amount',
                                     value=value,
                                     var='quantum')
            options['validate']['datatype'] = 'xs:integer'
            options['validate']['range'] = { 'minimum': 1, 'maximum': 5 }
            i = 1
            while i <= 5:
                x = str(i)
                options.addOption(x, x)
                i += 1
            value = Config.get_setting_value(self.settings, jid_bare, 'archive')
            value = str(value)
            options = form.add_field(desc='Number of news items to archive.',
                                     ftype='list-single',
                                     label='Archive',
                                     value=value,
                                     var='archive')
            options['validate']['datatype'] = 'xs:integer'
            options['validate']['range'] = { 'minimum': 0, 'maximum': 500 }
            i = 0
            while i <= 500:
                x = str(i)
                options.addOption(x, x)
                i += 50
            session['allow_complete'] = True
            # session['has_next'] = True
            session['next'] = self._handle_settings_complete
            session['payload'] = form
        else:
            if not is_operator(self, jid_bare):
                text_warn = 'This resource is restricted to operators.'
            elif chat_type == 'groupchat':
                text_warn = ('This resource is restricted to moderators of {}.'
                             .format(jid_bare))
            elif chat_type == 'error':
                text_warn = ('Could not determine chat type of {}.'
                             .format(jid_bare))
            else:
                text_warn = 'This resource is forbidden.'
            session['notes'] = [['warn', text_warn]]
        return session


    async def _handle_settings_complete(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                     .format(function_name, jid_full))
        jid_bare = session['from'].bare
        db_file = config.get_pathname_to_database(jid_bare)
        if jid_bare not in self.settings:
            Config.add_settings_jid(self.settings, jid_bare, db_file)
        # In this case (as is typical), the payload is a form
        values = payload['values']
        for key in values:
            val = values[key]

            if key in ('enabled', 'media', 'old'):
                if val == True:
                    val = 1
                elif val == False:
                    val = 0

            if key in ('archive', 'interval', 'quantum'):
                val = int(val)

            if key == 'interval':
                if val < 1: val = 1
                val = val * 60

            is_enabled = Config.get_setting_value(self.settings, jid_bare, 'enabled')

            if (key == 'enabled' and
                val == 1 and
                str(is_enabled) == 0):
                logger.info('Slixfeed has been enabled for {}'.format(jid_bare))
                status_type = 'available'
                status_message = '📫️ Welcome back!'
                XmppPresence.send(self, jid_bare, status_message,
                                  status_type=status_type)
                await asyncio.sleep(5)
                FeedTask.restart_task(self, jid_bare)
                XmppChatTask.restart_task(self, jid_bare)
                XmppStatusTask.restart_task(self, jid_bare)

            if (key == 'enabled' and
                val == 0 and
                str(is_enabled) == 1):
                logger.info('Slixfeed has been disabled for {}'.format(jid_bare))
                for task in ('interval', 'status'):
                    Task.stop(self, jid_bare, 'status')
                status_type = 'xa'
                status_message = '📪️ Send "Start" to receive updates'
                XmppPresence.send(self, jid_bare, status_message,
                                  status_type=status_type)

            await Config.set_setting_value(self.settings, jid_bare, db_file, key, val)
            val = self.settings[jid_bare][key]

            if key in ('enabled', 'media', 'old'):
                if val == '1':
                    val = 'Yes'
                elif val == '0':
                    val = 'No'

            if key == 'interval':
                val = int(val)
                val = val/60
                val = int(val)
                val = str(val)

        form = payload
        form['title'] = 'Done'
        form['instructions'] = 'has been completed!'
        # session['allow_complete'] = True
        # session['has_next'] = False
        # session['next'] = self._handle_profile
        session['payload'] = form
        return session
