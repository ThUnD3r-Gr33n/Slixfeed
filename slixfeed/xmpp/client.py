#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

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

1) Extracting attribute using xmltodict.
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

import slixfeed.action as action
import slixfeed.config as config
from slixfeed.dt import timestamp
import slixfeed.sqlite as sqlite
from slixfeed.xmpp.bookmark import XmppBookmark
from slixfeed.xmpp.connect import XmppConnect
from slixfeed.xmpp.muc import XmppGroupchat
from slixfeed.xmpp.message import XmppMessage
import slixfeed.xmpp.process as process
import slixfeed.xmpp.profile as profile
from slixfeed.xmpp.roster import XmppRoster
# import slixfeed.xmpp.service as service
from slixfeed.xmpp.presence import XmppPresence
from slixfeed.xmpp.upload import XmppUpload
from slixfeed.xmpp.utility import get_chat_type

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

        # Initialize event loop
        # self.loop = asyncio.get_event_loop()

        self.add_event_handler('connection_failed',
                               self.on_connection_failed)
        self.add_event_handler('session_end',
                               self.on_session_end)


    # TODO Test
    async def on_groupchat_invite(self, message):
        logging.warning("on_groupchat_invite")
        inviter = message['from'].bare
        muc_jid = message['groupchat_invite']['jid']
        await XmppBookmark.add(self, muc_jid)
        XmppGroupchat.join(self, inviter, muc_jid)
        message_body = ('Greetings! I am {}, the news anchor.\n'
                        'My job is to bring you the latest '
                        'news from sources you provide me with.\n'
                        'You may always reach me via xmpp:{}?message'
                        .format(self.alias, self.boundjid.bare))
        XmppMessage.send(self, muc_jid, message_body, 'groupchat')


    # NOTE Tested with Gajim and Psi
    async def on_groupchat_direct_invite(self, message):
        inviter = message['from'].bare
        muc_jid = message['groupchat_invite']['jid']
        await XmppBookmark.add(self, muc_jid)
        XmppGroupchat.join(self, inviter, muc_jid)
        message_body = ('Greetings! I am {}, the news anchor.\n'
                        'My job is to bring you the latest '
                        'news from sources you provide me with.\n'
                        'You may always reach me via xmpp:{}?message'
                        .format(self.alias, self.boundjid.bare))
        XmppMessage.send(self, muc_jid, message_body, 'groupchat')


    async def on_session_end(self, event):
        message = 'Session has ended.'
        await XmppConnect.recover(self, message)


    async def on_connection_failed(self, event):
        message = 'Connection has failed.  Reason: {}'.format(event)
        await XmppConnect.recover(self, message)


    async def on_session_start(self, event):
        # self.send_presence()
        profile.set_identity(self, 'client')
        self.service_commands()
        self.service_reactions()
        await self['xep_0115'].update_caps()
        await self.get_roster()
        await profile.update(self)
        task.task_ping(self)
        bookmarks = await self.plugin['xep_0048'].get_bookmarks()
        XmppGroupchat.autojoin(self, bookmarks)
        
        # Service.commands(self)
        # Service.reactions(self)
        


    def on_session_resumed(self, event):
        # self.send_presence()
        profile.set_identity(self, 'client')
        # self.service_commands()
        # self.service_reactions()
        self['xep_0115'].update_caps()
        XmppGroupchat.autojoin(self)
        
        # Service.commands(self)
        # Service.reactions(self)
        


    async def on_disco_info(self, DiscoInfo):
        jid = DiscoInfo['from']
        # self.service_commands()
        # self.service_reactions()
        # self.send_presence(pto=jid)
        await self['xep_0115'].update_caps(jid=jid)


    # TODO Request for subscription
    async def on_message(self, message):
        jid = message["from"].bare
        if (await get_chat_type(self, jid) == 'chat' and
            not self.client_roster[jid]['to']):
            XmppPresence.subscription(self, jid, 'subscribe')
            await XmppRoster.add(self, jid)
            status_message = '✒️ Share online status to receive updates'
            XmppPresence.send(self, jid, status_message)
            message_subject = 'RSS News Bot'
            message_body = 'Share online status to receive updates.'
            XmppMessage.send_headline(self, jid, message_subject, message_body,
                                      'chat')
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
        XmppRoster.remove(self, jid)


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


# TODO Move class Command to a separate file
# class Command(Slixfeed):
#     def __init__(self):
#         super().__init__()


    def service_commands(self):
        # self["xep_0050"].add_command(
        #     node="updates_enable",
        #     name="Enable/Disable News Updates",
        #     handler=option_enable_updates,
        #     )

        # if jid == config.get_value('accounts', 'XMPP', 'operator'):
        self['xep_0050'].add_command(node='subscriptions',
                                     name='📰️  Subscriptions',
                                     handler=self._handle_subscriptions)
        # self['xep_0050'].add_command(node='subscriptions_cat',
        #                              name='🔖️ Categories',
        #                              handler=self._handle_subscription)
        # self['xep_0050'].add_command(node='subscriptions_tag',
        #                              name='🏷️ Tags',
        #                              handler=self._handle_subscription)
        # self['xep_0050'].add_command(node='subscriptions_index',
        #                              name='📑️ Index (A - Z)',
        #                              handler=self._handle_subscription)
        self['xep_0050'].add_command(node='settings',
                                     name='📮️ Settings',
                                     handler=self._handle_settings)
        self['xep_0050'].add_command(node='filters',
                                     name='🛡️ Filters',
                                     handler=self._handle_filters)
        self['xep_0050'].add_command(node='bookmarks',
                                      name='📕 Bookmarks',
                                      handler=self._handle_bookmarks)
        # self['xep_0050'].add_command(node='roster',
        #                               name='📓 Roster', # 📋
        #                               handler=self._handle_roster)
        self['xep_0050'].add_command(node='help',
                                     name='📔️ Manual',
                                     handler=self._handle_help)
        self['xep_0050'].add_command(node='totd',
                                     name='💡️ TOTD',
                                     handler=self._handle_totd)
        self['xep_0050'].add_command(node='fotd',
                                     name='🗓️ FOTD',
                                     handler=self._handle_fotd)
        self['xep_0050'].add_command(node='activity',
                                     name='📠️ Activity',
                                     handler=self._handle_activity)
        self['xep_0050'].add_command(node='statistics',
                                     name='📊️ Statistics',
                                     handler=self._handle_statistics)
        self['xep_0050'].add_command(node='import',
                                     name='📥️ Import',
                                     handler=self._handle_import)
        self['xep_0050'].add_command(node='export',
                                     name='📤️ Export',
                                     handler=self._handle_export)
        self['xep_0050'].add_command(node='privacy',
                                     name='Privacy',
                                     handler=self._handle_privacy)
        self['xep_0050'].add_command(node='credit',
                                     name='Credits', # 💡️
                                     handler=self._handle_credit)
        self['xep_0050'].add_command(node='about',
                                     name='About', # 📜️
                                     handler=self._handle_about)
        # self['xep_0050'].add_command(node='search',
        #                              name='Search',
        #                              handler=self._handle_search)

    # Special interface
    # http://jabber.org/protocol/commands#actions

    async def _handle_filters(self, iq, session):
        jid = session['from'].bare
        jid_file = jid
        db_file = config.get_pathname_to_database(jid_file)
        form = self['xep_0004'].make_form('form',
                                          'Filters for {}'.format(jid))
        form['instructions'] = '🕸️ Manage filters' # 🪄️
        value  = await sqlite.get_filters_value(db_file, 'allow')
        form.add_field(var='allow',
                       ftype='text-single',
                       label='Allow list',
                       value=value,
                       desc=('Keywords to allow (comma-separated keywords).'))
        value  = await sqlite.get_filters_value(db_file, 'deny')
        form.add_field(var='deny',
                       ftype='text-single',
                       label='Deny list',
                       value=value,
                       desc=('Keywords to deny (comma-separated keywords).'))
        session['payload'] = form
        session['next'] = self._handle_filters_complete
        session['has_next'] = True
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
        # Text is not displayed; only labels
        form = payload

        jid = session['from'].bare
        form = self['xep_0004'].make_form('form', 'Filters for {}'.format(jid))
        form['instructions'] = ('✅️ Filters have been updated')
        jid_file = jid
        db_file = config.get_pathname_to_database(jid_file)
        # In this case (as is typical), the payload is a form
        values = payload['values']
        for value in values:
            key = value
            val = values[value]
            # NOTE We might want to add new keywords from
            #      an empty form instead of editing a form.
            # keywords = await sqlite.get_filters_value(db_file, key)
            keywords = ''
            val = await config.add_to_list(val, keywords)
            if await sqlite.get_filters_value(db_file, key):
                await sqlite.update_filters_value(db_file, [key, val])
            else:
                await sqlite.set_filters_value(db_file, [key, val])
            # result = '{}: {}'.format(key, val)
            form.add_field(var=key + '_title',
                           ftype='fixed',
                           value=key.capitalize() + ' filter')
            form.add_field(var=key.capitalize() + ' list',
                           ftype='text-single',
                           value=val)
        session['payload'] = form
        session["has_next"] = False
        session['next'] = None
        return session


    async def _handle_subscriptions(self, iq, session):
        jid = session['from'].bare
        form = self['xep_0004'].make_form('form',
                                          'Subscriptions for {}'.format(jid))
        form['instructions'] = '📰️ Manage subscriptions'
        # form.addField(var='interval',
        #               ftype='text-single',
        #               label='Interval period')
        options = form.add_field(var='subscriptions',
                                 ftype='list-multi',
                                 label='Subscriptions',
                                 desc=('Select subscriptions to perform '
                                       'actions upon.'),
                                 required=True)
        jid_file = jid
        db_file = config.get_pathname_to_database(jid_file)
        subscriptions = await sqlite.get_feeds(db_file)
        subscriptions = sorted(subscriptions, key=lambda x: x[0])
        for subscription in subscriptions:
            title = subscription[0]
            url = subscription[1]
            options.addOption(title, url)
        # options = form.add_field(var='action',
        #                          ftype='list-single',
        #                          label='Action',
        #                          value='none')
        # options.addOption('None', 'none')
        # options.addOption('Reset', 'reset')
        # options.addOption('Enable', 'enable')
        # options.addOption('Disable', 'disable')
        # options.addOption('Delete', 'delete')
        session['payload'] = form
        session['next'] = self._handle_subscription_editor
        session['has_next'] = True
        # Other useful session values:
        # session['to']                    -- The JID that received the
        #                                     command request.
        # session['from']                  -- The JID that sent the
        #                                     command request.
        # session['has_next'] = True       -- There are more steps to complete
        # session['allow_complete'] = True -- Allow user to finish immediately
        #                                     and possibly skip steps
        # session['cancel'] = handler      -- Assign a handler for if the user
        #                                     cancels the command.
        # session['notes'] = [             -- Add informative notes about the
        #   ('info', 'Info message'),         command's results.
        #   ('warning', 'Warning message'),
        #   ('error', 'Error message')]
        return session


    # FIXME There are feeds that are missing (possibly because of sortings)
    async def _handle_subscription(self, iq, session):
        jid = session['from'].bare
        form = self['xep_0004'].make_form('form',
                                          'Subscriptions for {}'.format(jid))
        form['instructions'] = '📰️ Edit subscription'
        # form.addField(var='interval',
        #               ftype='text-single',
        #               label='Interval period')
        jid_file = jid
        db_file = config.get_pathname_to_database(jid_file)
        subscriptions = await sqlite.get_feeds(db_file)
        # subscriptions = set(subscriptions)
        categorized_subscriptions = {}
        for subscription in subscriptions:
            title = subscription[0]
            url = subscription[1]
            try:
                letter = title[0].capitalize()
                if letter not in categorized_subscriptions:
                    categorized_subscriptions[letter] = [subscription]
                        # title[0].capitalize()] = [subscription]
                else:
                    categorized_subscriptions[letter].append(subscription)
                        # title[0].capitalize()].append(subscription)
            except Exception as e:
                logging.warning('Title might be empty:', str(e))
        for category in sorted(categorized_subscriptions):
            options = form.add_field(var=category,
                                     ftype='list-single',
                                     label=category.capitalize(),
                                     desc='Select a subscription to view.')
            subscriptions_ = categorized_subscriptions[category]
            subscriptions_ = sorted(subscriptions_, key=lambda x: x[0])
            for subscription_ in subscriptions_:
            # for subscription in categorized_subscriptions[category]:
                # breakpoint()
                title = subscription_[0]
                url = subscription_[1]
                options.addOption(title, url)
        session['payload'] = form
        session['next'] = self._handle_subscription_editor
        session['has_next'] = True
        return session


    async def _handle_subscription_editor(self, payload, session):
        urls = payload['values']['subscriptions']
        jid = session['from'].bare
        jid_file = jid
        db_file = config.get_pathname_to_database(jid_file)
        url_count = len(urls)
        if url_count > 1:
            form = self['xep_0004'].make_form('form', 'Subscription editor')
            form['instructions'] = '📂️ Editing {} subscriptions'.format(url_count)
            form.add_field(var='options',
                           ftype='fixed',
                           value='Options')
            options = form.add_field(var='action',
                                     ftype='list-single',
                                     label='Action',
                                     value='none')
            options.addOption('None', 'none')
            counter = 0
            for url in urls:
                feed_id = await sqlite.get_feed_id(db_file, url)
                feed_id = feed_id[0]
                count = sqlite.get_number_of_unread_entries_by_feed(db_file, feed_id)
                counter += count[0]
            if int(counter):
                options.addOption('Mark {} entries as read'.format(counter), 'reset')
            options.addOption('Delete {} subscriptions'.format(url_count), 'delete')
            options.addOption('Export {} subscriptions'.format(url_count), 'export')
        else:
            url = urls[0]
            feed_id = await sqlite.get_feed_id(db_file, url)
            feed_id = feed_id[0]
            title = sqlite.get_feed_title(db_file, feed_id)
            title = title[0]
            form = self['xep_0004'].make_form('form', 'Subscription editor')
            form['instructions'] = '📂️ Editing subscription #{}'.format(feed_id)
            form.add_field(var='properties',
                           ftype='fixed',
                           value='Properties')
            form.add_field(var='name',
                           ftype='text-single',
                           label='Name',
                           value=title)
            # NOTE This does not look good in Gajim
            # options = form.add_field(var='url',
            #                           ftype='fixed',
            #                           value=url)
            form.add_field(var='url',
                           ftype='text-single',
                           label='URL',
                           value=url)
            form.add_field(var='options',
                           ftype='fixed',
                           value='Options')
            options = form.add_field(var='action',
                                     ftype='list-single',
                                     label='Action',
                                     value='none')
            options.addOption('None', 'none')
            count = sqlite.get_number_of_unread_entries_by_feed(db_file, feed_id)
            count = count[0]
            if int(count):
                options.addOption('Mark {} entries as read'.format(count), 'reset')
            options.addOption('Delete subscription', 'delete')
        form.add_field(var='enable',
                       ftype='boolean',
                       label='Enable',
                       value=True)
        options = form.add_field(var='priority',
                                 ftype='list-single',
                                 label='Priority',
                                 value='0')
        options['validate']['datatype'] = 'xs:integer'
        options['validate']['range'] = { 'minimum': 1, 'maximum': 5 }
        i = 0
        while i <= 5:
            num = str(i)
            options.addOption(num, num)
            i += 1
        form.add_field(var='labels',
                       ftype='fixed',
                       value='Labels')
        options = form.add_field(var='category',
                                 ftype='list-single',
                                 label='Category',
                                 value='none')
        options.addOption('None', 'none')
        options.addOption('Activity', 'activity')
        options.addOption('Catalogues', 'catalogues')
        options.addOption('Clubs', 'clubs')
        options.addOption('Events', 'events')
        options.addOption('Forums', 'forums')
        options.addOption('Music', 'music')
        options.addOption('News', 'news')
        options.addOption('Organizations', 'organizations')
        options.addOption('Podcasts', 'podcasts')
        options.addOption('Projects', 'projects')
        options.addOption('Schools', 'schools')
        options.addOption('Stores', 'stores')
        options.addOption('Tutorials', 'tutorials')
        options.addOption('Videos', 'videos')
        options = form.add_field(var='tags',
                                 ftype='text-single',
                                 # ftype='text-multi',
                                 label='Tags',
                                 value='')
        session['payload'] = form
        session['next'] = self._handle_subscription_complete
        session['has_next'] = True
        return session


    async def _handle_subscription_complete(self, payload, session):
        form = self['xep_0004'].make_form('form', 'Subscription editor')
        form['instructions'] = ('📁️ Subscription #{} has been {}'
                                .format(feed_id, action))
        pass


    async def _handle_about(self, iq, session):
        # form = self['xep_0004'].make_form('result', 'Thanks')
        # form['instructions'] = action.manual('information.toml', 'thanks')
        # session['payload'] = form
        # text = '💡️ About Slixfeed, slixmpp and XMPP\n\n'
        # text += '\n\n'
        # form = self['xep_0004'].make_form('result', 'About')
        text = 'Slixfeed\n\n'
        text += ''.join(action.manual('information.toml', 'about'))
        text += '\n\n'
        text += 'Slixmpp\n\n'
        text += ''.join(action.manual('information.toml', 'slixmpp'))
        text += '\n\n'
        text += 'SleekXMPP\n\n'
        text += ''.join(action.manual('information.toml', 'sleekxmpp'))
        text += '\n\n'
        text += 'XMPP\n\n'
        text += ''.join(action.manual('information.toml', 'xmpp'))
        session['notes'] = [['info', text]]
        # form.add_field(var='about',
        #                ftype='text-multi',
        #                label='About',
        #                value=text)
        # session['payload'] = form
        return session


    async def _handle_activity(self, iq, session):
        # TODO dialog for JID and special dialog for operator
        text = ('Here you can monitor activity')
        session['notes'] = [['info', text]]
        return session


    async def _handle_statistics(self, iq, session):
        text = ('Here you can monitor statistics')
        session['notes'] = [['info', text]]
        return session


    async def _handle_import(self, iq, session):
        jid = session['from'].bare
        form = self['xep_0004'].make_form('form',
                                          'Import data for {}'.format(jid))
        form['instructions'] = '🗞️ Import feeds from OPML'
        form.add_field(var='url',
                       ftype='text-single',
                       label='URL',
                       desc='Enter URL to OPML file.',
                       required=True)
        session['payload'] = form
        session['next'] = self._handle_import_complete
        session['has_next'] = True
        return session


    async def _handle_import_complete(self, payload, session):
        session['next'] = None
        url = payload['values']['url']
        if url.startswith('http') and url.endswith('.opml'):
            jid = session['from'].bare
            jid_file = jid.replace('/', '_')
            db_file = config.get_pathname_to_database(jid_file)
            count = await action.import_opml(db_file, url)
            try:
                int(count)
                form = self['xep_0004'].make_form('result',
                                                  'Import data for {}'.format(jid))
                form['instructions'] = ('✅️ Feeds have been imported')
                message = '{} feeds have been imported to {}.'.format(count, jid)
                form.add_field(var='message',
                               ftype='text-single',
                               value=message)
                session['payload'] = form
                session["has_next"] = False
            except:
                session['notes'] = [['error', 'Import failed. Filetype does not appear to be an OPML file.']]
                session['has_next'] = False
        else:
            session['notes'] = [['error', 'Import aborted. Send URL of OPML file.']]
            session['has_next'] = False
        return session


    async def _handle_export(self, iq, session):
        jid = session['from'].bare
        form = self['xep_0004'].make_form('form',
                                          'Export data for {}'.format(jid))
        form['instructions'] = '🗞️ Export feeds'
        options = form.add_field(var='filetype',
                                 ftype='list-multi',
                                 label='Format',
                                 desc='Choose export format.',
                                 value='opml',
                                 required=True)
        options.addOption('Markdown', 'md')
        options.addOption('OPML', 'opml')
        # options.addOption('HTML', 'html')
        # options.addOption('XBEL', 'xbel')
        session['payload'] = form
        session['next'] = self._handle_export_complete
        session['has_next'] = True
        return session


    async def _handle_export_complete(self, payload, session):
        jid = session['from'].bare
        jid_file = jid.replace('/', '_')
        form = self['xep_0004'].make_form('result',
                                          'Export data for {}'.format(jid))
        form['instructions'] = ('✅️ Feeds have been exported')
        exts = payload['values']['filetype']
        for ext in exts:
            filename = await action.export_feeds(self, jid, jid_file, ext)
            url = await XmppUpload.start(self, jid, filename)
            form.add_field(var=ext.upper(),
                            ftype='text-single',
                            label=ext,
                            value=url)
        session['payload'] = form
        session["has_next"] = False
        session['next'] = None
        return session


    async def _handle_privacy(self, iq, session):
        text = ('Privacy Policy')
        text += '\n\n'
        text += ''.join(action.manual('information.toml', 'privacy'))
        session['notes'] = [['info', text]]
        return session


    async def _handle_fotd(self, iq, session):
        text = ('Here we publish featured news feeds!')
        session['notes'] = [['info', text]]
        return session


    async def _handle_motd(self, iq, session):
        # TODO add functionality to attach image.
        text = ('Here you can add groupchat rules,post schedule, tasks or '
                'anything elaborated you might deem fit. Good luck!')
        session['notes'] = [['info', text]]
        return session


    async def _handle_totd(self, iq, session):
        text = ('Tips and tricks you might have not known about Slixfeed and XMPP!')
        session['notes'] = [['info', text]]
        return session


    async def _handle_credit(self, iq, session):
        # form = self['xep_0004'].make_form('result', 'Thanks')
        # form['instructions'] = action.manual('information.toml', 'thanks')
        # session['payload'] = form
        text = 'We are XMPP\n\n'
        fren = action.manual('information.toml', 'thanks')
        fren = "".join(fren)
        fren = fren.split(';')
        fren = "\n".join(fren)
        text += fren
        # text += '\n\nYOU!\n\n🫵️\n\n- Join us -\n\n🤝️'
        text += '\n\nYOU!\n\n🫵️\n\n- Join us -'
        session['notes'] = [['info', text]]
        return session


    async def _handle_help(self, iq, session):
        filename = 'commands.toml'
        import tomllib
        config_dir = config.get_default_config_directory()
        with open(config_dir + '/' + filename, mode="rb") as commands:
            cmds = tomllib.load(commands)

        form = self['xep_0004'].make_form('result', 'Manual')
        form['instructions'] = '🛟️ Help manual for interactive chat'

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
                           value=name)
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


    async def _handle_bookmarks(self, iq, session):
        jid = session['from'].bare
        if jid == config.get_value('accounts', 'XMPP', 'operator'):
            form = self['xep_0004'].make_form('form', 'Bookmarks')
            form['instructions'] = '📖️ Organize bookmarks'
            options = form.add_field(var='bookmarks',
                                     ftype='list-single',
                                     label='Select a bookmark',
                                     desc='Select a bookmark to edit.')
            conferences = await XmppBookmark.get(self)
            for conference in conferences:
                options.addOption(conference['name'], conference['jid'])
            session['payload'] = form
            session['next'] = self._handle_bookmarks_editor
            session['has_next'] = True
        else:
            logging.warning('An unauthorized attempt to access bookmarks has '
                            'been detected!\n'
                            'Details:\n'
                            '   Jabber ID: {}\n'
                            '   Timestamp: {}\n'
                            .format(jid, timestamp()))
            session['notes'] = [['error', 'You are not allowed to access this resource.']]
        return session


    async def _handle_bookmarks_editor(self, payload, session):
        jid = payload['values']['bookmarks']
        properties = await XmppBookmark.properties(self, jid)
        jid = session['from'].bare
        form = self['xep_0004'].make_form('form', 'Edit bookmark')
        form['instructions'] = '📝️ Edit bookmark {}'.format(properties['name'])
        jid = properties['jid'].split('@')
        room = jid[0]
        host = jid[1]
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
        form.addField(var='alias',
                      ftype='text-single',
                      label='Alias',
                      value=properties['nick'],
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
        session['payload'] = form
        session['next'] = self._handle_bookmarks_complete
        session['has_next'] = True
        return session


    async def _handle_bookmarks_complete(self, payload, session):
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

        form = self['xep_0004'].make_form('result', 'Bookmarks')
        form['instructions'] = ('✅️ Bookmark has been saved')
        # In this case (as is typical), the payload is a form
        values = payload['values']
        await XmppBookmark.add(self, properties=values)
        for value in values:
            key = str(value)
            val = str(values[value])
            if not val: val = 'None' # '(empty)'
            form.add_field(var=key,
                            ftype='text-single',
                            label=key.capitalize(),
                            value=val)
        session['payload'] = form # Comment when this is fixed in Gajim
        session["has_next"] = False
        session['next'] = None
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
        jid = session['from'].bare
        jid_file = jid
        db_file = config.get_pathname_to_database(jid_file)
        form = self['xep_0004'].make_form('form',
                                          'Settings for {}'.format(jid))
        form['instructions'] = ('📮️ Customize news updates')

        value = config.get_setting_value(db_file, 'enabled')
        value = int(value)
        if value:
            value = True
        else:
            value = False
        form.add_field(var='enabled',
                       ftype='boolean',
                       label='Enable',
                       desc='Enable news updates.',
                       value=value)

        value = config.get_setting_value(db_file, 'media')
        value = int(value)
        if value:
            value = True
        else:
            value = False
        form.add_field(var='media',
                       ftype='boolean',
                       desc='Send audio, images or videos if found.',
                       label='Display media',
                       value=value)

        value = config.get_setting_value(db_file, 'old')
        value = int(value)
        if value:
            value = True
        else:
            value = False
        form.add_field(var='old',
                       ftype='boolean',
                       desc='Send old items of newly added subscriptions.',
                       # label='Send only new items',
                       label='Include old news',
                       value=value)

        value = config.get_setting_value(db_file, 'interval')
        value = int(value)
        value = value/60
        value = int(value)
        value = str(value)
        options = form.add_field(var='interval',
                                 ftype='list-single',
                                 label='Interval',
                                 desc='Set interval update (in hours).',
                                 value=value)
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

        value = config.get_setting_value(db_file, 'archive')
        value = str(value)
        options = form.add_field(var='archive',
                                 ftype='list-single',
                                 label='Archive',
                                 desc='Number of news items to archive.',
                                 value=value)
        options['validate']['datatype'] = 'xs:integer'
        options['validate']['range'] = { 'minimum': 0, 'maximum': 500 }
        i = 0
        while i <= 500:
            x = str(i)
            options.addOption(x, x)
            i += 50

        value = config.get_setting_value(db_file, 'quantum')
        value = str(value)
        options = form.add_field(var='quantum',
                                 ftype='list-single',
                                 label='Amount',
                                 desc='Set amount of items per update.',
                                 value=value)
        options['validate']['datatype'] = 'xs:integer'
        options['validate']['range'] = { 'minimum': 1, 'maximum': 5 }
        i = 1
        while i <= 5:
            x = str(i)
            options.addOption(x, x)
            i += 1

        session['payload'] = form
        session['next'] = self._handle_settings_complete
        session['has_next'] = False
        return session


    async def _handle_settings_complete(self, payload, session):
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
        # This looks nice in Gajim, though there are dropdown menues
        # form = payload

        jid = session['from'].bare
        form = self['xep_0004'].make_form('form',
                                          'Settings for {}'.format(jid))
        form['instructions'] = ('✅️ Settings have been saved')

        jid_file = jid
        db_file = config.get_pathname_to_database(jid_file)
        # In this case (as is typical), the payload is a form
        values = payload['values']
        for value in values:
            key = value
            val = values[value]

            if key == 'interval':
                val = int(val)
                if val < 1: val = 1
                val = val * 60

            if sqlite.get_settings_value(db_file, key):
                await sqlite.update_settings_value(db_file, [key, val])
            else:
                await sqlite.set_settings_value(db_file, [key, val])

            val = sqlite.get_settings_value(db_file, key)
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

            # match value:
            #     case 'enabled':
            #         pass
            #     case 'interval':
            #         pass

            result = '{}: {}'.format(key.capitalize(), val)

            form.add_field(var=key,
                            ftype='fixed',
                            value=result)
        session['payload'] = form # Comment when this is fixed in Gajim
        session["has_next"] = False
        session['next'] = None
        # return session
