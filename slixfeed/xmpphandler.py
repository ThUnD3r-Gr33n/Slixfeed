#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

import asyncio
import os
import slixmpp

import confighandler
import datahandler
import sqlitehandler

jid_tasker = {}
task_manager = {}

time_now = datetime.now()
# time_now = time_now.strftime("%H:%M:%S")

def print_time():
    # return datetime.now().strftime("%H:%M:%S")
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    return current_time


class Slixfeed(slixmpp.ClientXMPP):
    """
    Slixmpp news bot that will send updates
    from feeds it receives.
    """

    print("slixmpp.ClientXMPP")
    print(repr(slixmpp.ClientXMPP))

    def __init__(self, jid, password):
        slixmpp.ClientXMPP.__init__(self, jid, password)

        # The session_start event will be triggered when
        # the bot establishes its connection with the server
        # and the XML streams are ready for use. We want to
        # listen for this event so that we we can initialize
        # our roster.
        self.add_event_handler("session_start", self.start)
        # self.add_event_handler("session_start", self.select_file)
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
        await self.select_file()

        self.send_presence(
            pshow="away",
            pstatus="Slixmpp has been restarted.",
            pto="sch@pimux.de"
        )


    async def message(self, msg):
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
        if msg["type"] in ("chat", "normal"):
            action = 0
            jid = msg["from"].bare
            message = " ".join(msg["body"].split())
            message = message.lower()
            if message.startswith("help"):
                action = print_help()
            # NOTE: Might not need it
            # elif message.startswith("add "):
            #     url = message[4:]
            elif message.startswith("http"):
                url = message
                action = await initdb(jid, datahandler.add_feed, url)
                # action = "> " + message + "\n" + action
            elif message.startswith("quantum "):
                key = message[:7]
                val = message[8:]
                # action = "Every update will contain {} news items.".format(action)
                action = await initdb(jid, sqlitehandler.set_settings_value, [key, val])
                await self.refresh_task(jid, key, val)
            elif message.startswith("interval "):
                key = message[:8]
                val = message[9:]
                # action = "Updates will be sent every {} minutes.".format(action)
                action = await initdb(jid, sqlitehandler.set_settings_value, [key, val])
                await self.refresh_task(jid, key, val)
            elif message.startswith("list"):
                action = await initdb(jid, sqlitehandler.list_subscriptions)
            elif message.startswith("recent "):
                num = message[7:]
                action = await initdb(jid, sqlitehandler.last_entries, num)
            elif message.startswith("remove "):
                ix = message[7:]
                action = await initdb(jid, sqlitehandler.remove_feed, ix)
            elif message.startswith("search "):
                query = message[7:]
                action = await initdb(jid, sqlitehandler.search_entries, query)
            elif message.startswith("start"):
                # action = "Updates are enabled."
                key = "enabled"
                val = 1
                actiona = await initdb(jid, sqlitehandler.set_settings_value, [key, val])
                asyncio.create_task(self.task_jid(jid))
                # print(print_time(), "task_manager[jid]")
                # print(task_manager[jid])
            elif message.startswith("stats"):
                action = await initdb(jid, sqlitehandler.statistics)
            elif message.startswith("status "):
                ix = message[7:]
                action = await initdb(jid, sqlitehandler.toggle_status, ix)
            elif message.startswith("stop"):
                # action = "Updates are disabled."
                try:
                    task_manager[jid]["check"].cancel()
                    # task_manager[jid]["status"].cancel()
                    task_manager[jid]["interval"].cancel()
                    key = "enabled"
                    val = 0
                    actiona = await initdb(jid, sqlitehandler.set_settings_value, [key, val])
                    await self.send_status(jid)
                    print(print_time(), "task_manager[jid]")
                    print(task_manager[jid])
                except:
                    # action = "Updates are already disabled."
                    await self.send_status(jid)
            else:
                action = "Unknown command. Press \"help\" for list of commands"
            if action: msg.reply(action).send()

            print(print_time(), "COMMAND ACCOUNT")
            print("COMMAND:", message)
            print("ACCOUNT: " + str(msg["from"]))


    async def select_file(self):
        """
        Initiate actions by JID (Jabber ID).

        :param self: Self
        """
        while True:
            db_dir = confighandler.get_default_dbdir()
            if not os.path.isdir(db_dir):
                msg = ("Slixfeed can not work without a database. \n"
                       "To create a database, follow these steps: \n"
                       "Add Slixfeed contact to your roster \n"
                       "Send a feed to the bot by: \n"
                       "add https://reclaimthenet.org/feed/")
                print(print_time(), msg)
                print(msg)
            else:
                os.chdir(db_dir)
                files = os.listdir()
            # TODO Use loop (with gather) instead of TaskGroup
            # for file in files:
            #     if file.endswith(".db") and not file.endswith(".db-jour.db"):
            #         jid = file[:-3]
            #         jid_tasker[jid] = asyncio.create_task(self.task_jid(jid))
            #         await jid_tasker[jid]
            async with asyncio.TaskGroup() as tg:
                print("main task")
                print(print_time(), "repr(tg)")
                print(repr(tg)) # <TaskGroup entered>
                for file in files:
                    if file.endswith(".db") and not file.endswith(".db-jour.db"):
                        jid = file[:-3]
                        tg.create_task(self.task_jid(jid))
                        # task_manager.update({jid: tg})
                        # print(task_manager) # {}
                        print(print_time(), "repr(tg) id(tg)")
                        print(jid, repr(tg)) # sch@pimux.de <TaskGroup tasks=1 entered>
                        print(jid, id(tg)) # sch@pimux.de 139879835500624
                        # <xmpphandler.Slixfeed object at 0x7f24922124d0> <TaskGroup tasks=2 entered>
                        # <xmpphandler.Slixfeed object at 0x7f24922124d0> 139879835500624


    async def task_jid(self, jid):
        """
        JID (Jabber ID) task manager.

        :param self: Self
        :param jid: Jabber ID
        """
        enabled = await initdb(
            jid,
            sqlitehandler.get_settings_value,
            "enabled"
        )
        print(print_time(), "enabled", enabled, jid)
        if enabled:
            print("sub task")
            print(print_time(), "repr(self) id(self)")
            print(repr(self))
            print(id(self))
            task_manager[jid] = {}
            task_manager[jid]["check"] = asyncio.create_task(check_updates(jid))
            task_manager[jid]["status"] = asyncio.create_task(self.send_status(jid))
            task_manager[jid]["interval"] = asyncio.create_task(self.send_update(jid))
            await task_manager[jid]["check"]
            await task_manager[jid]["status"]
            await task_manager[jid]["interval"]
            print(print_time(), "task_manager[jid].items()")
            print(task_manager[jid].items())
            print(print_time(), "task_manager[jid]")
            print(task_manager[jid])
            print(print_time(), "task_manager")
            print(task_manager)
        else:
            await self.send_status(jid)

    async def send_update(self, jid):
        """
        Send news items as messages.

        :param self: Self
        :param jid: Jabber ID
        """
        new = await initdb(
            jid,
            sqlitehandler.get_entry_unread
        )
        if new:
            print(print_time(), "> SEND UPDATE",jid)
            self.send_message(
                mto=jid,
                mbody=new,
                mtype="chat"
            )
        interval = await initdb(
            jid,
            sqlitehandler.get_settings_value,
            "interval"
        )
        # await asyncio.sleep(60 * interval)
        self.loop.call_at(
            self.loop.time() + 60 * interval,
            self.loop.create_task,
            self.send_update(jid)
        )

    async def send_status(self, jid):
        """
        Send status message.

        :param self: Self
        :param jid: Jabber ID
        """
        print(print_time(), "> SEND STATUS",jid)
        unread = await initdb(
            jid,
            sqlitehandler.get_number_of_entries_unread
        )

        if unread:
            status_text = "📰 News items: {}".format(str(unread))
            status_mode = "chat"
        else:
            status_text = "🗞 No News"
            status_mode = "available"

        enabled = await initdb(
            jid,
            sqlitehandler.get_settings_value,
            "enabled"
        )
        
        if not enabled:
            status_mode = "xa"

        # print(status_text, "for", jid)
        self.send_presence(
            pshow=status_mode,
            pstatus=status_text,
            pto=jid,
            #pfrom=None
        )

        await asyncio.sleep(60 * 20)

        # self.loop.call_at(
        #     self.loop.time() + 60 * 20,
        #     self.loop.create_task,
        #     self.send_status(jid)
        # )


    async def refresh_task(self, jid, key, val):
        """
        Apply settings on runtime.

        :param self: Self
        :param jid: Jabber ID
        :param key: Key
        :param val: Value
        """
        if jid in task_manager:
            task_manager[jid][key].cancel()
            loop = asyncio.get_event_loop()
            print(print_time(), "loop")
            print(loop)
            print(print_time(), "loop")
            task_manager[jid][key] = loop.call_at(
                loop.time() + 60 * float(val),
                loop.create_task,
                self.send_update(jid)
            )
            # task_manager[jid][key] = self.send_update.loop.call_at(
            #     self.send_update.loop.time() + 60 * val,
            #     self.send_update.loop.create_task,
            #     self.send_update(jid)
            # )


# TODO Take this function out of
# <class 'slixmpp.clientxmpp.ClientXMPP'>
async def check_updates(jid):
    """
    Start calling for update check up.

    :param jid: Jabber ID
    """
    while True:
        print(print_time(), "> CHCK UPDATE",jid)
        await initdb(jid, datahandler.download_updates)
        await asyncio.sleep(60 * 90)
        # Schedule to call this function again in 90 minutes
        # self.loop.call_at(
        #     self.loop.time() + 60 * 90,
        #     self.loop.create_task,
        #     self.check_updates(jid)
        # )


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
           " start \n"
           "   Enable bot and send updates. \n"
           " Stop \n"
           "   Disable bot and stop updates. \n"
           " batch N \n"
           "   Send N updates for each interval. \n"
           " interval N \n"
           "   Send an update every N minutes. \n"
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
