#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
import slixmpp

import confighandler
import datahandler
import sqlitehandler

task_manager = {}

class Slixfeed(slixmpp.ClientXMPP):
    """
    Slixmpp news bot that will send updates
    from feeds it receives.
    """
    def __init__(self, jid, password):
        slixmpp.ClientXMPP.__init__(self, jid, password)

        # The session_start event will be triggered when
        # the bot establishes its connection with the server
        # and the XML streams are ready for use. We want to
        # listen for this event so that we we can initialize
        # our roster.
        self.add_event_handler("session_start", self.start)
        self.add_event_handler("session_start", self.select_file)
        # self.add_event_handler("session_start", self.send_status)
        # self.add_event_handler("session_start", self.check_updates)

        # The message event is triggered whenever a message
        # stanza is received. Be aware that that includes
        # MUC messages and error messages.
        self.add_event_handler("message", self.message)
        self.add_event_handler("disconnected", self.reconnect)
        # Initialize event loop
        self.loop = asyncio.get_event_loop()

    async def start(self, event):
        """
        Process the session_start event.

        Typical actions for the session_start event are
        requesting the roster and broadcasting an initial
        presence stanza.

        Arguments:
            event -- An empty dictionary. The session_start
                     event does not provide any additional
                     data.
        """
        self.send_presence()
        await self.get_roster()

    async def message(self, event, msg):
        """
        Process incoming message stanzas. Be aware that this also
        includes MUC messages and error messages. It is usually
        a good idea to check the messages's type before processing
        or sending replies.

        Arguments:
            msg -- The received message stanza. See the documentation
                   for stanza objects and the Message stanza to see
                   how it may be used.
        """
        if msg['type'] in ('chat', 'normal'):
            jid = msg['from'].bare
            message = " ".join(msg['body'].split())
            if message.lower().startswith('help'):
                action = print_help()
            # NOTE: Might not need it
            elif message.lower().startswith('add '):
                action = await initdb(jid, datahandler.add_feed, message[4:])
                # action = "> " + message + "\n" + action
            elif message.lower().startswith('quantum '):
                key = message[:7]
                val = message[8:]
                # action = "Every update will contain {} news items.".format(action)
                action = await initdb(jid, sqlitehandler.set_settings_value, [key, val])
                await self.refresh_task(jid, key, val)
            elif message.lower().startswith('disable'):
                # action = "Updates are disabled."
                action = await initdb(jid, sqlitehandler.set_settings_value, message)
                await self.refresh_task(jid, "enabled", 0)
            elif message.lower().startswith('enable'):
                # action = "Updates are enabled."
                action = await initdb(jid, sqlitehandler.set_settings_value, message)
                await self.refresh_task(jid, "enabled", 1)
            elif message.lower().startswith('interval '):
                key = message[:8]
                val = message[9:]
                # action = "Updates will be sent every {} minutes.".format(action)
                action = await initdb(jid, sqlitehandler.set_settings_value, [key, val])
                await self.refresh_task(event, jid, key, val)
            elif message.lower().startswith('list'):
                action = await initdb(jid, sqlitehandler.list_subscriptions)
            elif message.lower().startswith('recent '):
                action = await initdb(jid, sqlitehandler.last_entries, message[7:])
            elif message.lower().startswith('remove '):
                action = await initdb(jid, sqlitehandler.remove_feed, message[7:])
            elif message.lower().startswith('search '):
                action = await initdb(jid, sqlitehandler.search_entries, message[7:])
            elif message.lower().startswith('status '):
                action = await initdb(jid, sqlitehandler.toggle_status, message[7:])
            elif message.lower().startswith('unread'):
                action = await initdb(jid, sqlitehandler.statistics)
            else:
                action = "Unknown command. Press \"help\" for list of commands"
            msg.reply(action).send()

            print("COMMAND:", message)
            print("ACCOUNT: " + str(msg['from']))

    async def select_file(self, event):
        """
        Initiate actions by JID (Jabber ID).

        :param self: Self
        :param event: Event
        """
        while True:
            db_dir = confighandler.get_default_dbdir()
            if not os.path.isdir(db_dir):
                msg = ("Slixfeed can not work without a database. \n"
                       "To create a database, follow these steps: \n"
                       "Add Slixfeed contact to your roster \n"
                       "Send a feed to the bot by: \n"
                       "add https://reclaimthenet.org/feed/")
                print(msg)
            else:
                os.chdir(db_dir)
                files = os.listdir()
                async with asyncio.TaskGroup() as tg:
                    print("main task")
                    print(repr(tg))
                    for file in files:
                        if file.endswith('.db') and not file.endswith('.db-jour.db'):
                            jid = file[:-3]
                            tg.create_task(self.jid(event, jid))
                            # task_manager.update({jid: tg})
                            print(task_manager)
                            print(jid, repr(tg))
                            print(jid, id(tg))

    async def jid(self, event, jid):
        """
        JID (Jabber ID) task manager.

        :param self: Self
        :param event: Event
        :param jid: Jabber ID
        """
        enabled = await initdb(
            jid,
            sqlitehandler.get_settings_value,
            'enabled'
        )
        print("enabled", enabled, jid)
        if enabled:
            async with asyncio.TaskGroup() as tg:
                print("sub task")
                print(repr(self))
                print(id(self))
                print(repr(tg))
                print(id(tg))
                tg.create_task(self.check_updates(event, jid))
                # tg.create_task(self.send_update(event, jid))
                task_manager[jid] = {}
                task_manager[jid]['interval'] = tg.create_task(self.send_update(event, jid))
                print(task_manager[jid])
                tg.create_task(self.send_status(event, jid))
        else:
            await self.send_status(event, jid)

    async def check_updates(self, event, jid):
        """
        Start calling for update check up.

        :param self: Self
        :param event: Event
        :param jid: Jabber ID
        """
        while True:
            print("> CHCK UPDATE",jid)
            await initdb(jid, datahandler.download_updates)
            await asyncio.sleep(60 * 90)
            # Schedule to call this function again in 90 minutes
            # self.loop.call_at(self.loop.time() + 60 * 90, self.loop.create_task, self.check_updates(event, jid))

    async def send_update(self, event, jid):
        """
        Send news items as messages.

        :param self: Self
        :param event: Event
        :param jid: Jabber ID
        """
        new = await initdb(
            jid,
            sqlitehandler.get_entry_unread
        )
        if new:
            print("> SEND UPDATE",jid)
            self.send_message(
                mto=jid,
                mbody=new,
                mtype='chat'
            )
        interval = await initdb(
            jid,
            sqlitehandler.get_settings_value,
            'interval'
        )
        # await asyncio.sleep(60 * interval)
        self.loop.call_at(self.loop.time() + 60 * interval, self.loop.create_task, self.send_update(event, jid))

    async def send_status(self, event, jid):
        """
        Send status message.

        :param self: Self
        :param event: Event
        :param jid: Jabber ID
        """
        print("> SEND STATUS",jid)
        unread = await initdb(
            jid,
            sqlitehandler.get_number_of_entries_unread
        )

        if unread:
            msg_status = "📰 News items: {}".format(str(unread))
            typ_status = "chat"
        else:
            msg_status = "🗞 No News"
            typ_status = "available"

        enabled = await initdb(
            jid,
            sqlitehandler.get_settings_value,
            'enabled'
        )
        
        if not enabled:
            typ_status = "xa"

        # print(msg_status, 'for', jid)
        self.send_presence(
            pshow=typ_status,
            pstatus=msg_status,
            pto=jid,
            #pfrom=None
        )
        # await asyncio.sleep(60 * 20)
        self.loop.call_at(self.loop.time() + 60 * 20, self.loop.create_task, self.send_status(event, jid))


    async def refresh_task(self, event, jid, key, val):
        """
        Apply settings on runtime.

        :param self: Self
        :param jid: Jabber ID
        :param key: Key
        :param val: Value
        """
        if jid in task_manager:
            task_manager[jid][key].cancel()
            task_manager[jid][key] = self.send_update.loop.call_at(
                self.send_update.loop.time() + 60 * val,
                self.send_update.loop.create_task,
                self.send_update(event, jid)
            )

def print_help():
    """
    Print help manual.
    """
    msg = ("Slixfeed - News syndication bot for Jabber/XMPP \n"
           "\n"
           "DESCRIPTION: \n"
           " Slixfeed is a news aggregator bot for online news feeds. \n"
           " Supported filetypes: Atom, RDF and RSS. \n"
           "\n"
           "BASIC USAGE: \n"
           " enable \n"
           "   Send updates. \n"
           " disable \n"
           "   Stop sending updates. \n"
           " batch N \n"
           "   Send N updates on ech interval. \n"
           " interval N \n"
           "   Send an update each N minutes. \n"
           " feed list \n"
           "   List subscriptions. \n"
           "\n"
           "EDIT OPTIONS: \n"
           " add URL \n"
           "   Add URL to subscription list. \n"
           " remove ID \n"
           "   Remove feed from subscription list. \n"
           " status ID \n"
           "   Toggle update status of feed. \n"
           "\n"
           "SEARCH OPTIONS: \n"
           " search TEXT \n"
           "   Search news items by given keywords. \n"
           " recent N \n"
           "   List recent N news items (up to 50 items). \n"
           "\n"
           "STATISTICS OPTIONS: \n"
           " analyses \n"
           "   Show report and statistics of feeds. \n"
           " obsolete \n"
           "   List feeds that are not available. \n"
           " unread \n"
           "   Print number of unread news items. \n"
           "\n"
           "BACKUP OPTIONS: \n"
           " export opml \n"
           "   Send an OPML file with your feeds. \n"
           " backup news html\n"
           "   Send an HTML formatted file of your news items. \n"
           " backup news md \n"
           "   Send a Markdown file of your news items. \n"
           " backup news text \n"
           "   Send a Plain Text file of your news items. \n"
           "\n"
           "DOCUMENTATION: \n"
           " Slixfeed \n"
           "   https://gitgud.io/sjehuda/slixfeed \n"
           " Slixmpp \n"
           "   https://slixmpp.readthedocs.io/ \n"
           " feedparser \n"
           "   https://pythonhosted.org/feedparser")
    return msg


# TODO Perhaps this needs to be executed
# just once per program execution
async def initdb(jid, callback, message=None):
    """
    Callback function to instantiate action on database.
    
    :param jid: JID (Jabber ID).
    :param callback: Function name.
    :param massage: Optional kwarg when a message is a part or required argument.
    """
    db_dir = confighandler.get_default_dbdir()
    if not os.path.isdir(db_dir):
        os.mkdir(db_dir)
    db_file = os.path.join(db_dir, r"{}.db".format(jid))
    sqlitehandler.create_tables(db_file)
    # await sqlitehandler.set_default_values(db_file)
    if message:
        return await callback(db_file, message)
    else:
        return await callback(db_file)
