#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

TODO

1) Deprecate "add" (see above) and make it interactive.
   Slixfeed: Do you still want to add this URL to subscription list?
   See: case _ if message_lowercase.startswith("add"):

2) Use loop (with gather) instead of TaskGroup

"""

import asyncio
import os
import slixmpp

from slixmpp.plugins.xep_0363.http_upload import FileTooBig, HTTPError, UploadServiceNotFound

import confighandler
import datahandler
import datetimehandler
import filterhandler
import sqlitehandler

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


async def handle_event():
  print("Event handled!")


class Slixfeed(slixmpp.ClientXMPP):
    """
    Slixmpp
    -------
    News bot that sends updates from RSS feeds.
    """
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
        # self.loop = asyncio.get_event_loop()


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

        # for task in main_task:
        #     task.cancel()
        if not main_task:
            await self.select_file()


    async def message(self, msg):
        """
        Process incoming message stanzas. Be aware that this also
        includes MUC messages and error messages. It is usually
        a good practice to check the messages's type before
        processing or sending replies.

        Parameters
        ----------
        self : ?
            Self.
        msg : str
            The received message stanza. See the documentation
            for stanza objects and the Message stanza to see
            how it may be used.
        """
        if msg["type"] in ("chat", "normal"):
            action = 0
            jid = msg["from"].bare

            db_dir = confighandler.get_default_dbdir()
            os.chdir(db_dir)
            if jid + ".db" not in os.listdir():
                await self.task_jid(jid)

            message = " ".join(msg["body"].split())
            message_lowercase = message.lower()

            print(await datetimehandler.current_time(), "ACCOUNT: " + str(msg["from"]))
            print(await datetimehandler.current_time(), "COMMAND:", message)

            match message_lowercase:
                case "help":
                    action = print_help()
                case _ if message_lowercase in ["greetings", "hello", "hey"]:
                    action = (
                        "Greeting! I'm Slixfeed The News Bot!"
                        "\n"
                        "Send a URL of a news website to start."
                        )
                case _ if message_lowercase.startswith("add"):
                    message = message[4:]
                    url = message.split(" ")[0]
                    title = " ".join(message.split(" ")[1:])
                    if url.startswith("http"):
                        action = await datahandler.initdb(
                            jid,
                            datahandler.add_feed_no_check,
                            [url, title]
                            )
                        await self.send_status(jid)
                    else:
                        action = "Missing URL."
                case _ if message_lowercase.startswith("allow"):
                        key = "filter-" + message[:5]
                        val = message[6:]
                        if val:
                            keywords = await datahandler.initdb(
                                jid,
                                sqlitehandler.get_settings_value,
                                key
                                )
                            val = await filterhandler.set_filter(
                                val,
                                keywords
                                )
                            await datahandler.initdb(
                                jid,
                                sqlitehandler.set_settings_value,
                                [key, val]
                                )
                            action = (
                                "Approved keywords\n"
                                "```\n{}\n```"
                                ).format(val)
                        else:
                            action = "Missing keywords."
                case _ if message_lowercase.startswith("deny"):
                        key = "filter-" + message[:4]
                        val = message[5:]
                        if val:
                            keywords = await datahandler.initdb(
                                jid,
                                sqlitehandler.get_settings_value,
                                key
                                )
                            val = await filterhandler.set_filter(
                                val,
                                keywords
                                )
                            await datahandler.initdb(
                                jid,
                                sqlitehandler.set_settings_value,
                                [key, val]
                                )
                            action = (
                                "Rejected keywords\n"
                                "```\n{}\n```"
                                ).format(val)
                        else:
                            action = "Missing keywords."
                case _ if message_lowercase.startswith("http"):
                    url = message
                    action = await datahandler.initdb(
                        jid,
                        datahandler.add_feed,
                        url
                        )
                    # action = "> " + message + "\n" + action
                    await self.send_status(jid)
                case _ if message_lowercase.startswith("feeds"):
                    query = message[6:]
                    if query:
                        if len(query) > 3:
                            action = await datahandler.initdb(
                                jid,
                                sqlitehandler.search_feeds,
                                query
                                )
                        else:
                            action = (
                                "Enter at least 4 characters to search"
                                )
                    else:
                        action = await datahandler.initdb(
                            jid,
                            sqlitehandler.list_feeds
                            )
                case _ if message_lowercase.startswith("interval"):
                # FIXME
                # The following error occurs only upon first attempt to set interval.
                # /usr/lib/python3.11/asyncio/events.py:73: RuntimeWarning: coroutine 'Slixfeed.send_update' was never awaited
                # self._args = None
                # RuntimeWarning: Enable tracemalloc to get the object allocation traceback
                    key = message[:8]
                    val = message[9:]
                    if val:
                        # action = (
                        #     "Updates will be sent every {} minutes."
                        #     ).format(action)
                        await datahandler.initdb(
                            jid,
                            sqlitehandler.set_settings_value,
                            [key, val]
                            )
                        await self.refresh_task(
                            jid,
                            self.send_update,
                            key,
                            val
                            )
                        action = (
                            "Updates will be sent every {} minutes."
                            ).format(val)
                    else:
                        action = "Missing value."
                case _ if message_lowercase.startswith("next"):
                    num = message[5:]
                    await self.send_update(jid, num)
                    await self.send_status(jid)
                    # await self.refresh_task(jid, key, val)
                case _ if message_lowercase.startswith("quantum"):
                    key = message[:7]
                    val = message[8:]
                    if val:
                        # action = (
                        #     "Every update will contain {} news items."
                        #     ).format(action)
                        await datahandler.initdb(
                            jid,
                            sqlitehandler.set_settings_value,
                            [key, val]
                            )
                        action = (
                            "Next update will contain {} news items."
                            ).format(val)
                    else:
                        action = "Missing value."
                case _ if message_lowercase.startswith("random"):
                    action = "Updates will be sent randomly."
                case _ if message_lowercase.startswith("recent"):
                    num = message[7:]
                    if num:
                        action = await datahandler.initdb(
                            jid,
                            sqlitehandler.last_entries,
                            num
                            )
                    else:
                        action = "Missing value."
                case _ if message_lowercase.startswith("remove"):
                    ix = message[7:]
                    if ix:
                        action = await datahandler.initdb(
                            jid,
                            sqlitehandler.remove_feed,
                            ix
                            )
                        await self.send_status(jid)
                    else:
                        action = "Missing feed ID."
                case _ if message_lowercase.startswith("search"):
                    query = message[7:]
                    if query:
                        if len(query) > 1:
                            action = await datahandler.initdb(
                                jid,
                                sqlitehandler.search_entries,
                                query
                                )
                        else:
                            action = (
                                "Enter at least 2 characters to search"
                                )
                    else:
                        action = "Missing search query."
                case "start":
                    # action = "Updates are enabled."
                    key = "enabled"
                    val = 1
                    await datahandler.initdb(
                        jid,
                        sqlitehandler.set_settings_value,
                        [key, val]
                        )
                    asyncio.create_task(self.task_jid(jid))
                    action = "Updates are enabled."
                    # print(await datetimehandler.current_time(), "task_manager[jid]")
                    # print(task_manager[jid])
                case "stats":
                    action = await datahandler.initdb(
                        jid,
                        sqlitehandler.statistics
                        )
                case _ if message_lowercase.startswith("status "):
                    ix = message[7:]
                    action = await datahandler.initdb(
                        jid,
                        sqlitehandler.toggle_status,
                        ix
                        )
                case "stop":
                # FIXME
                # The following error occurs only upon first attempt to stop.
                # /usr/lib/python3.11/asyncio/events.py:73: RuntimeWarning: coroutine 'Slixfeed.send_update' was never awaited
                # self._args = None
                # RuntimeWarning: Enable tracemalloc to get the object allocation traceback
                # action = "Updates are disabled."
                    # try:
                    #     # task_manager[jid]["check"].cancel()
                    #     # task_manager[jid]["status"].cancel()
                    #     task_manager[jid]["interval"].cancel()
                    #     key = "enabled"
                    #     val = 0
                    #     action = await datahandler.initdb(
                    #         jid,
                    #         sqlitehandler.set_settings_value,
                    #         [key, val]
                    #         )
                    # except:
                    #     action = "Updates are already disabled."
                    #     # print("Updates are already disabled. Nothing to do.")
                    # # await self.send_status(jid)
                    key = "enabled"
                    val = 0
                    await datahandler.initdb(
                        jid,
                        sqlitehandler.set_settings_value,
                        [key, val]
                        )
                    await self.task_jid(jid)
                    action = "Updates are disabled."
                case "support":
                    # TODO Send an invitation.
                    action = "xmpp:slixmpp@muc.poez.io?join"
                case _:
                    action = (
                        "Unknown command. "
                        "Press \"help\" for list of commands"
                        )
            if action: msg.reply(action).send()


    async def select_file(self):
        """
        Initiate actions by JID (Jabber ID).

        Parameters
        ----------
        self : ?
            Self.
        """
        while True:
            db_dir = confighandler.get_default_dbdir()
            if not os.path.isdir(db_dir):
                msg = (
                    "Slixfeed can not work without a database.\n"
                    "To create a database, follow these steps:\n"
                    "Add Slixfeed contact to your roster.\n"
                    "Send a feed to the bot by URL:\n"
                    "https://reclaimthenet.org/feed/"
                    )
                # print(await datetimehandler.current_time(), msg)
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
                for file in files:
                    if file.endswith(".db") and not file.endswith(".db-jour.db"):
                        jid = file[:-3]
                        main_task.extend([tg.create_task(self.task_jid(jid))])
                        # main_task = [tg.create_task(self.task_jid(jid))]
                        # task_manager.update({jid: tg})


    async def task_jid(self, jid):
        """
        JID (Jabber ID) task manager.

        Parameters
        ----------
        self : ?
            Self.
        jid : str
            Jabber ID.
        """
        enabled = await datahandler.initdb(
            jid,
            sqlitehandler.get_settings_value,
            "enabled"
        )
        # print(await datetimehandler.current_time(), "enabled", enabled, jid)
        if enabled:
            task_manager[jid] = {}
            task_manager[jid]["check"] = asyncio.create_task(
                check_updates(jid)
                )
            task_manager[jid]["status"] = asyncio.create_task(
                self.send_status(jid)
                )
            task_manager[jid]["interval"] = asyncio.create_task(
                self.send_update(jid)
                )
            await task_manager[jid]["check"]
            await task_manager[jid]["status"]
            await task_manager[jid]["interval"]
        else:
            # FIXME
            # The following error occurs only upon first attempt to stop.
            # /usr/lib/python3.11/asyncio/events.py:73: RuntimeWarning: coroutine 'Slixfeed.send_update' was never awaited
            # self._args = None
            # RuntimeWarning: Enable tracemalloc to get the object allocation traceback
            try:
                task_manager[jid]["interval"].cancel()
            except:
                None
            await self.send_status(jid)


    async def send_update(self, jid, num=None):
        """
        Send news items as messages.

        Parameters
        ----------
        self : ?
            Self.
        jid : str
            Jabber ID.
        num : str, optional
            Number. The default is None.
        """
        # print("Starting send_update()")
        # print(jid)
        new = await datahandler.initdb(
            jid,
            sqlitehandler.get_entry_unread,
            num
        )
        if new:
            print(await datetimehandler.current_time(), "> SEND UPDATE",jid)
            self.send_message(
                mto=jid,
                mbody=new,
                mtype="chat"
            )
        await self.refresh_task(
            jid,
            self.send_update,
            "interval"
            )
        # interval = await datahandler.initdb(
        #     jid,
        #     sqlitehandler.get_settings_value,
        #     "interval"
        # )
        # task_manager[jid]["interval"] = loop.call_at(
        #     loop.time() + 60 * interval,
        #     loop.create_task,
        #     self.send_update(jid)
        # )

        # print(await datetimehandler.current_time(), "asyncio.get_event_loop().time()")
        # print(await datetimehandler.current_time(), asyncio.get_event_loop().time())
        # await asyncio.sleep(60 * interval)

        # loop.call_later(
        #     60 * interval,
        #     loop.create_task,
        #     self.send_update(jid)
        # )

        # print
        # await handle_event()


    async def send_status(self, jid):
        """
        Send status message.

        Parameters
        ----------
        self : ?
            Self.
        jid : str
            Jabber ID.
        """
        print(await datetimehandler.current_time(), "> SEND STATUS",jid)
        enabled = await datahandler.initdb(
            jid,
            sqlitehandler.get_settings_value,
            "enabled"
        )
        if not enabled:
            status_mode = "xa"
            status_text = "Send \"Start\" to receive news."
        else:
            feeds = await datahandler.initdb(
                jid,
                sqlitehandler.get_number_of_items,
                "feeds"
            )
            if not feeds:
                status_mode = "available"
                status_text = (
                    "📂️ Send a URL from a blog or a news website."
                    )
            else:
                unread = await datahandler.initdb(
                    jid,
                    sqlitehandler.get_number_of_entries_unread
                )
                if unread:
                    status_mode = "chat"
                    status_text = (
                        "📰 You have {} news items to read."
                        ).format(str(unread))
                    # status_text = (
                    #     "📰 News items: {}"
                    #     ).format(str(unread))
                    # status_text = (
                    #     "📰 You have {} news items"
                    #     ).format(str(unread))
                else:
                    status_mode = "available"
                    status_text = "🗞 No news"

        # print(status_text, "for", jid)
        self.send_presence(
            pshow=status_mode,
            pstatus=status_text,
            pto=jid,
            #pfrom=None
            )
        # await asyncio.sleep(60 * 20)
        await self.refresh_task(
            jid,
            self.send_status,
            "status",
            "20"
            )
        # loop.call_at(
        #     loop.time() + 60 * 20,
        #     loop.create_task,
        #     self.send_status(jid)
        # )


    async def refresh_task(self, jid, callback, key, val=None):
        """
        Apply new setting at runtime.

        Parameters
        ----------
        self : ?
            Self.
        jid : str
            Jabber ID.
        key : str
            Key.
        val : str, optional
            Value. The default is None.
        """
        if not val:
            val = await datahandler.initdb(
                jid,
                sqlitehandler.get_settings_value,
                key
                )
        if jid in task_manager:
            task_manager[jid][key].cancel()
            task_manager[jid][key] = loop.call_at(
                loop.time() + 60 * float(val),
                loop.create_task,
                callback(jid)
                # self.send_update(jid)
            )
            # task_manager[jid][key] = loop.call_later(
            #     60 * float(val),
            #     loop.create_task,
            #     self.send_update(jid)
            # )
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

    Parameters
    ----------
    jid : str
        Jabber ID.
    """
    while True:
        print(await datetimehandler.current_time(), "> CHCK UPDATE",jid)
        await datahandler.initdb(jid, datahandler.download_updates)
        await asyncio.sleep(60 * 90)
        # Schedule to call this function again in 90 minutes
        # loop.call_at(
        #     loop.time() + 60 * 90,
        #     loop.create_task,
        #     self.check_updates(jid)
        # )


def print_help():
    """
    Print help manual.

    Returns
    -------
    msg : str
        Message.
    """
    msg = (
        "```\n"
        "NAME\n"
        "Slixfeed - News syndication bot for Jabber/XMPP\n"
        "\n"
        "DESCRIPTION\n"
        " Slixfeed is a news aggregator bot for online news feeds.\n"
        " This program is primarily designed for XMPP.\n"
        " For more information, visit https://xmpp.org/software/\n"
        "\n"
        "BASIC USAGE\n"
        " start\n"
        "   Enable bot and send updates.\n"
        " stop\n"
        "   Disable bot and stop updates.\n"
        " feeds\n"
        "   List subscriptions.\n"
        " interval N\n"
        "   Set interval update to every N minutes.\n"
        " next N\n"
        "   Send N next updates.\n"
        " quantum N\n"
        "   Set N updates for each interval.\n"
        "\n"
        "FILTER OPTIONS\n"
        " allow\n"
        "   Keywords to allow (comma separates).\n"
        " deny\n"
        "   Keywords to block (comma separates).\n"
        # " filter clear allow\n"
        # "   Reset allow list.\n"
        # " filter clear deny\n"
        # "   Reset deny list.\n"
        "\n"
        "EDIT OPTIONS\n"
        " URL\n"
        "   Add URL to subscription list.\n"
        " add URL TITLE\n"
        "   Add URL to subscription list (without validity check).\n"
        " remove ID\n"
        "   Remove feed from subscription list.\n"
        " status ID\n"
        "   Toggle update status of feed.\n"
        "\n"
        "SEARCH OPTIONS\n"
        " feeds TEXT\n"
        "   Search subscriptions by given keywords.\n"
        " search TEXT\n"
        "   Search news items by given keywords.\n"
        " recent N\n"
        "   List recent N news items (up to 50 items).\n"
        "\n"
        # "STATISTICS OPTIONS\n"
        # " analyses\n"
        # "   Show report and statistics of feeds.\n"
        # " obsolete\n"
        # "   List feeds that are not available.\n"
        # " unread\n"
        # "   Print number of unread news items.\n"
        # "\n"
        # "BACKUP OPTIONS\n"
        # " export opml\n"
        # "   Send an OPML file with your feeds.\n"
        # " backup news html\n"
        # "   Send an HTML formatted file of your news items.\n"
        # " backup news md\n"
        # "   Send a Markdown file of your news items.\n"
        # " backup news text\n"
        # "   Send a Plain Text file of your news items.\n"
        # "\n"
        "SUPPORT\n"
        " support"
        "   Join xmpp:slixmpp@muc.poez.io?join\n"
        "\n"
        # "PROTOCOLS\n"
        # " Supported prootcols are IRC, Matrix and XMPP.\n"
        # " For the best experience, we recommend you to use XMPP.\n"
        # "\n"
        "FILETYPES\n"
        " Supported filetypes are Atom, RDF and RSS.\n"
        "\n"
        "AUTHORS\n"
        " Laura Harbinger, Schimon Zackary.\n"
        "\n"
        "COPYRIGHT\n"
        " Slixfeed is free software; you can redistribute it and/or\n"
        " modify it under the terms of the GNU General Public License\n"
        " as published by the Free Software Foundation; version 3 only\n"
        "\n"
        " Slixfeed is distributed in the hope that it will be useful,\n"
        " but WITHOUT ANY WARRANTY; without even the implied warranty of\n"
        " MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the\n"
        " GNU General Public License for more details.\n"
        "\n"
        "NOTE\n"
        " Make Slixfeed your own.\n"
        "\n"
        " You can run Slixfeed on your own computer, server, and\n"
        " even on a Linux phone (i.e. Droidian, Mobian NixOS,\n"
        " postmarketOS). You can also use Termux.\n"
        "\n"
        " All you need is one of the above and an XMPP account to\n"
        " connect Slixfeed to.\n"
        "\n"
        "DOCUMENTATION\n"
        " Slixfeed\n"
        "   https://gitgud.io/sjehuda/slixfeed\n"
        " Slixmpp\n"
        "   https://slixmpp.readthedocs.io/\n"
        " feedparser\n"
        "   https://pythonhosted.org/feedparser\n"
        "\n```"
        )
    return msg
