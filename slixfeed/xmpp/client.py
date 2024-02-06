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

import slixfeed.config as config
import slixfeed.sqlite as sqlite
from slixfeed.xmpp.bookmark import XmppBookmark
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
        await XmppBookmark.add(self, muc_jid)


    # NOTE Tested with Gajim and Psi
    async def on_groupchat_direct_invite(self, message):
        inviter = message["from"].bare
        muc_jid = message['groupchat_invite']['jid']
        await muc.join(self, inviter, muc_jid)
        await XmppBookmark.add(self, muc_jid)


    async def on_session_end(self, event):
        message = "Session has ended."
        await connect.recover_connection(self, message)


    async def on_connection_failed(self, event):
        message = "Connection has failed.  Reason: {}".format(event)
        await connect.recover_connection(self, message)


    async def on_session_start(self, event):
        self.send_presence()
        await self["xep_0115"].update_caps()
        await self.get_roster()
        await muc.autojoin(self)
        profile.set_identity(self, "client")
        await profile.update(self)
        task.ping_task(self)
        
        # Service.commands(self)
        # Service.reactions(self)
        
        self.service_commands()
        self.service_reactions()


    async def on_session_resumed(self, event):
        self.send_presence()
        self["xep_0115"].update_caps()
        await muc.autojoin(self)
        profile.set_identity(self, "client")
        
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
        #     self['xep_0050'].add_command(node='bookmarks',
        #                                  name='Bookmarks',
        #                                  handler=self._handle_bookmarks)
        #     self['xep_0050'].add_command(node='roster',
        #                                  name='Roster',
        #                                  handler=self._handle_roster)
        self['xep_0050'].add_command(node='settings',
                                     name='Settings',
                                     handler=self._handle_settings)
        self['xep_0050'].add_command(node='subscriptions',
                                     name='Subscriptions',
                                     handler=self._handle_subscriptions)
        # self['xep_0050'].add_command(node='search',
        #                              name='Search',
        #                              handler=self._handle_search)
        # self['xep_0050'].add_command(node='filters',
        #                              name='Filters',
        #                              handler=self._handle_filters)


    async def _handle_subscriptions(self, iq, session):
        form = self['xep_0004'].make_form('form', 'Subscriptions')
        form['instructions'] = '📰️ Manage subscriptions.'
        # form.addField(var='interval',
        #               ftype='text-single',
        #               label='Interval period')
        options = form.add_field(var='subscriptions',
                                 ftype='list-multi',
                                 label='Select subscriptions',
                                 desc='Select subscription(s) to edit.')
        jid = session['from'].bare
        jid_file = jid
        db_file = config.get_pathname_to_database(jid_file)
        subscriptions = await sqlite.get_feeds(db_file)
        for subscription in subscriptions:
            title = subscription[0]
            url = subscription[1]
            options.addOption(title, url)
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


    # TODO Make form for a single subscription and several subscriptions
    # single: Delete, Disable, Reset and Rename
    # several: Delete, Disable, Reset
    async def _handle_subscription_editor(self, iq, session):
        form = self['xep_0004'].make_form('form', 'Subscriptions')
        form['instructions'] = '🗞️ Edit subscriptions.'
        options = form.add_field(var='enable',
                                 ftype='boolean',
                                 label='Enable',
                                 value=True)
        options = form.add_field(var='action',
                                 ftype='list-single',
                                 label='Action',
                                 value='reset')
        options.addOption('Delete', 'delete')
        options.addOption('Reset', 'reset')
        session['payload'] = form
        session['next'] = None
        session['has_next'] = False
        return session


    async def _handle_bookmarks(self, iq, session):
        form = self['xep_0004'].make_form('form', 'Bookmarks')
        form['instructions'] = '📑️ Organize bookmarks.'
        options = form.add_field(var='bookmarks',
                                 # ftype='list-multi'
                                 ftype='list-single',
                                 label='Select a bookmark',
                                 desc='Select a bookmark to edit.')
        conferences = await XmppBookmark.get(self)
        for conference in conferences:
            options.addOption(conference['jid'], conference['jid'])
        session['payload'] = form
        session['next'] = self._handle_command_complete
        session['has_next'] = False
        return session


    async def _handle_bookmarks_editor(self, iq, session):
        form = self['xep_0004'].make_form('form', 'Bookmarks')
        form['instructions'] = '📝️ Edit bookmarks.'
        form.addField(var='name',
                      ftype='text-single',
                      label='Name')
        form.addField(var='host',
                      ftype='text-single',
                      label='Host',
                      required=True)
        form.addField(var='room',
                      ftype='text-single',
                      label='Room',
                      required=True)
        form.addField(var='alias',
                      ftype='text-single',
                      label='Alias')
        form.addField(var='password',
                      ftype='text-private',
                      label='Password')
        form.add_field(var='autojoin',
                       ftype='boolean',
                       label='Auto-join',
                       value=True)
        options = form.add_field(var='action',
                       ftype='list-single',
                       label='Action',
                       value='join')
        options.addOption('Add', 'add')
        options.addOption('Join', 'join')
        options.addOption('Remove', 'remove')
        session['payload'] = form
        session['next'] = None
        session['has_next'] = False
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
        form = self['xep_0004'].make_form('form', 'Settings')
        form['instructions'] = ('📮️ Customize news updates.')
        jid = session['from'].bare
        jid_file = jid
        db_file = config.get_pathname_to_database(jid_file)
        value = await config.get_setting_value(db_file, 'enabled')
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
        value = await config.get_setting_value(db_file, 'old')
        value = int(value)
        if value:
            value = False
        else:
            value = True
        form.add_field(var='old',
                       ftype='boolean',
                       desc='Mark items of newly added subscriptions as read.',
                       # label='Send only new items',
                       label='Include old news',
                       value=value)
        value = await config.get_setting_value(db_file, 'interval')
        value = str(int(value/60))
        options = form.add_field(var='interval',
                                 ftype='list-single',
                                 label='Interval',
                                 desc='Set interval update (in hours).',
                                 value=value)
        i = 60
        while i <= 2880:
            var = str(i)
            lab = str(int(i/60))
            options.addOption(lab, var)
            i += 60
        value = await config.get_setting_value(db_file, 'archive')
        value = str(value)
        options = form.add_field(var='archive',
                                 ftype='list-single',
                                 label='Archive',
                                 desc='Number of news items to archive.',
                                 value=value)
        i = 0
        while i <= 500:
            x = str(i)
            options.addOption(x, x)
            i += 1
        value = await config.get_setting_value(db_file, 'quantum')
        value = str(value)
        options = form.add_field(var='quantum',
                                 ftype='list-single',
                                 label='Amount',
                                 desc='Set amount of updates per update.',
                                 value='3')
        i = 1
        while i <= 10:
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

        jid = session['from'].bare
        jid_file = jid
        db_file = config.get_pathname_to_database(jid_file)
        # In this case (as is typical), the payload is a form
        form = payload
        values = form['values']
        for value in values:
            key = value
            val = values[value]
            if await sqlite.get_settings_value(db_file, key):
                await sqlite.update_settings_value(db_file, [key, val])
            else:
                await sqlite.set_settings_value(db_file, [key, val])
            match value:
                case 'enabled':
                    pass
                case 'interval':
                    pass
        # Having no return statement is the same as unsetting the 'payload'
        # and 'next' session values and returning the session.
        # Unless it is the final step, always return the session dictionary.
        session['payload'] = None
        session['next'] = None
        return session
