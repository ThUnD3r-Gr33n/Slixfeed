#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

FIXME

1) Function check_readiness or event "changed_status" is causing for
   triple status messages and also false ones that indicate of lack
   of feeds.

TODO

1) Deprecate "add" (see above) and make it interactive.
   Slixfeed: Do you still want to add this URL to subscription list?
   See: case _ if message_lowercase.startswith("add"):

2) Use loop (with gather) instead of TaskGroup.

3) Assure message delivery before calling a new task.
    See https://slixmpp.readthedocs.io/en/latest/event_index.html#term-marker_acknowledged

4) Do not send updates when busy or away.
    See https://slixmpp.readthedocs.io/en/latest/event_index.html#term-changed_status

NOTE

1) Self presence
    Apparently, it is possible to view self presence.
    This means that there is no need to store presences in order to switch or restore presence.
    check_readiness
    <presence from="slixfeed@canchat.org/xAPgJLHtMMHF" xml:lang="en" id="ab35c07b63a444d0a7c0a9a0b272f301" to="slixfeed@canchat.org/xAPgJLHtMMHF"><status>📂 Send a URL from a blog or a news website.</status><x xmlns="vcard-temp:x:update"><photo /></x></presence>
    JID: self.boundjid.bare
    MUC: self.nick

2) Extracting attribute using xmltodict.
    import xmltodict
    message = xmltodict.parse(str(message))
    jid = message["message"]["x"]["@jid"]

"""

import asyncio
import logging
import os
import slixmpp
from random import randrange

from slixmpp.plugins.xep_0363.http_upload import FileTooBig, HTTPError, UploadServiceNotFound

import datahandler
import datetimehandler
import filehandler
import filterhandler
import sqlitehandler
import taskhandler

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
    Slixmpp
    -------
    News bot that sends updates from RSS feeds.
    """
    def __init__(self, jid, password, room=None, nick=None):
        slixmpp.ClientXMPP.__init__(self, jid, password)

        # The session_start event will be triggered when
        # the bot establishes its connection with the server
        # and the XML streams are ready for use. We want to
        # listen for this event so that we we can initialize
        # our roster.
        self.add_event_handler("session_start", self.start_session)
        self.add_event_handler("session_resumed", self.start_session)
        self.add_event_handler("got_offline", print("got_offline"))
        # self.add_event_handler("got_online", self.check_readiness)
        self.add_event_handler("changed_status", self.check_readiness)
        self.add_event_handler("presence_unavailable", self.stop_tasks)

        # self.add_event_handler("changed_subscription", self.check_subscription)

        # self.add_event_handler("chatstate_active", self.check_chatstate_active)
        # self.add_event_handler("chatstate_gone", self.check_chatstate_gone)
        self.add_event_handler("chatstate_composing", self.check_chatstate_composing)
        self.add_event_handler("chatstate_paused", self.check_chatstate_paused)

        # The message event is triggered whenever a message
        # stanza is received. Be aware that that includes
        # MUC messages and error messages.
        self.add_event_handler("message", self.message)
        self.add_event_handler("message", self.settle)

        self.add_event_handler("groupchat_invite", self.accept_muc_invite)
        self.add_event_handler("groupchat_direct_invite", self.accept_muc_invite)
        # self.add_event_handler("groupchat_message", self.message)

        # self.add_event_handler("disconnected", self.reconnect)
        # self.add_event_handler("disconnected", self.inspect_connection)

        self.add_event_handler("reactions", self.reactions)
        self.add_event_handler("presence_available", self.presence_available)
        self.add_event_handler("presence_error", self.presence_error)
        self.add_event_handler("presence_subscribe", self.presence_subscribe)
        self.add_event_handler("presence_subscribed", self.presence_subscribed)
        self.add_event_handler("presence_unsubscribe", self.presence_unsubscribe)
        self.add_event_handler("presence_unsubscribed", self.unsubscribe)

        # Initialize event loop
        # self.loop = asyncio.get_event_loop()

        # handlers for connection events
        self.connection_attempts = 0
        self.max_connection_attempts = 10
        self.add_event_handler("connection_failed", self.on_connection_failed)
        self.add_event_handler("session_end", self.on_session_end)

    """

    FIXME

    This function is triggered even when status is dnd/away/xa.
    This results in sending messages even when status is dnd/away/xa.
    See function check_readiness.
    
    NOTE

    The issue occurs only at bot startup.
    Once status is changed to dnd/away/xa, the interval stops - as expected.
    
    TODO

    Use "sleep()"

    """
    async def presence_available(self, presence):
        # print("def presence_available", presence["from"].bare)
        if presence["from"].bare not in self.boundjid.bare:
            jid = presence["from"].bare
            await taskhandler.clean_tasks_xmpp(
                jid,
                ["interval", "status", "check"]
                )
            await taskhandler.start_tasks_xmpp(
                self,
                jid,
                ["interval", "status", "check"]
                )
            # await taskhandler.task_jid(self, jid)
            # main_task.extend([asyncio.create_task(taskhandler.task_jid(jid))])
            # print(main_task)

    async def stop_tasks(self, presence):
        if not self.boundjid.bare:
            jid = presence["from"].bare
            print(">>> unavailable:", jid)
            await taskhandler.clean_tasks_xmpp(
                jid,
                ["interval", "status", "check"]
                )


    async def presence_error(self, presence):
        print("presence_error")
        print(presence)

    async def presence_subscribe(self, presence):
        print("presence_subscribe")
        print(presence)

    async def presence_subscribed(self, presence):
        print("presence_subscribed")
        print(presence)

    async def reactions(self, message):
        print("reactions")
        print(message)

    async def accept_muc_invite(self, message):
        ctr = message["from"].bare
        jid = message['groupchat_invite']['jid']
        tkn = randrange(10000, 99999)
        self.plugin['xep_0045'].join_muc(
            jid,
            "Slixfeed (RSS News Bot)",
            # If a room password is needed, use:
            # password=the_room_password,
            )
        self.send_message(
            mto=ctr,
            mbody=(
                "Send activation token {} to groupchat xmpp:{}?join."
                ).format(tkn, jid)
            )
        # self.add_event_handler(
        #     "muc::[room]::message",
        #     self.message
        #     )


    async def on_session_end(self, event):
        print(await datetimehandler.current_time(), "Session ended. Attempting to reconnect.")
        print(event)
        logging.warning("Session ended. Attempting to reconnect.")
        await self.recover_connection(event)


    async def on_connection_failed(self, event):
        print(await datetimehandler.current_time(), "Connection failed. Attempting to reconnect.")
        print(event)
        logging.warning("Connection failed. Attempting to reconnect.")
        await self.recover_connection(event)


    async def recover_connection(self, event):
        self.connection_attempts += 1
        # if self.connection_attempts <= self.max_connection_attempts:
        #     self.reconnect(wait=5.0)  # wait a bit before attempting to reconnect
        # else:
        #     print(await datetimehandler.current_time(),"Maximum connection attempts exceeded.")
        #     logging.error("Maximum connection attempts exceeded.")
        print("Attempt:", self.connection_attempts)
        self.reconnect(wait=5.0)


    async def inspect_connection(self, event):
        print("Disconnected\nReconnecting...")
        print(event)
        try:
            self.reconnect
        except:
            self.disconnect()
            print("Problem reconnecting")


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
        await taskhandler.refresh_task(
            self,
            jid,
            taskhandler.send_status,
            "status",
            20
            )


    async def check_readiness(self, presence):
        """
        If available, begin tasks.
        If unavailable, eliminate tasks.

        Parameters
        ----------
        presence : str
            XML stanza </presence>.

        Returns
        -------
        None.
        """
        # print("def check_readiness", presence["from"].bare, presence["type"])
        # # available unavailable away (chat) dnd xa
        # print(">>> type", presence["type"], presence["from"].bare)
        # # away chat dnd xa
        # print(">>> show", presence["show"], presence["from"].bare)

        jid = presence["from"].bare
        if presence["show"] in ("away", "dnd", "xa"):
            print(">>> away, dnd, xa:", jid)
            await taskhandler.clean_tasks_xmpp(
                jid,
                ["interval"]
                )
            await taskhandler.start_tasks_xmpp(
                self,
                jid,
                ["status", "check"]
                )


    async def resume(self, event):
        print("def resume")
        print(event)
        self.send_presence()
        await self.get_roster()


    async def start_session(self, event):
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
        print("def start_session")
        print(event)
        self.send_presence()
        await self.get_roster()

        # for task in main_task:
        #     task.cancel()

        # Deprecated in favour of event "presence_available"
        # if not main_task:
        #     await taskhandler.select_file()


    async def settle(self, msg):
        """
        Add JID to roster and settle subscription.

        Parameters
        ----------
        jid : str
            Jabber ID.

        Returns
        -------
        None.
        """
        jid = msg["from"].bare
        await self.get_roster()
        # Check whether JID is in roster; otherwise, add it.
        if jid not in self.client_roster.keys():
            self.send_presence_subscription(
                pto=jid,
                ptype="subscribe",
                pnick="Slixfeed RSS News Bot"
                )
            self.update_roster(
                jid,
                subscription="both"
                )
        # Check whether JID is subscribed; otherwise, ask for presence.
        if not self.client_roster[jid]["to"]:
            self.send_presence_subscription(
                pto=jid,
                pfrom=self.boundjid.bare,
                ptype="subscribe",
                pnick="Slixfeed RSS News Bot"
                )
            self.send_message(
                mto=jid,
                mtype="headline",
                msubject="RSS News Bot",
                mbody=("Accept subscription request to receive updates."),
                mfrom=self.boundjid.bare,
                mnick="Slixfeed RSS News Bot"
                )
            self.send_presence(
                pto=jid,
                pfrom=self.boundjid.bare,
                # Accept symbol 🉑️ 👍️ ✍
                pstatus="✒️ Accept subscription request to receive updates",
                # ptype="subscribe",
                pnick="Slixfeed RSS News Bot"
                )


    async def presence_unsubscribe(self, presence):
        print("presence_unsubscribe")
        print(presence)


    async def unsubscribe(self, presence):
        jid = presence["from"].bare
        self.send_presence(
            pto=jid,
            pfrom=self.boundjid.bare,
            pstatus="🖋️ Subscribe to receive updates",
            pnick="Slixfeed RSS News Bot"
            )
        self.send_message(
            mto=jid,
            mbody="You have been unsubscribed."
            )
        self.update_roster(
            jid,
            subscription="remove"
            )


    async def message(self, msg):
        """
        Process incoming message stanzas. Be aware that this also
        includes MUC messages and error messages. It is usually
        a good practice to check the messages's type before
        processing or sending replies.

        Parameters
        ----------
        msg : str
            The received message stanza. See the documentation
            for stanza objects and the Message stanza to see
            how it may be used.
        """
        # print("message")
        # print(msg)
        if msg["type"] in ("chat", "groupchat", "normal"):
            action = 0
            jid = msg["from"].bare
            if msg["type"] == "groupchat":
                ctr = await filehandler.initdb(
                    jid,
                    sqlitehandler.get_settings_value,
                    "masters"
                    )
                if (msg["from"][msg["from"].index("/")+1:] not in ctr
                    or not msg["body"].startswith("!")):
                    return
                    
            # # Begin processing new JID
            # # Deprecated in favour of event "presence_available"
            # db_dir = filehandler.get_default_dbdir()
            # os.chdir(db_dir)
            # if jid + ".db" not in os.listdir():
            #     await taskhandler.task_jid(jid)
            print(msg["body"])
            print(msg["body"].split())
            message = " ".join(msg["body"].split())
            if msg["type"] == "groupchat":
                message = message[1:]
            print(message)
            message_lowercase = message.lower()

            print(await datetimehandler.current_time(), "ACCOUNT: " + str(msg["from"]))
            print(await datetimehandler.current_time(), "COMMAND:", message)

            match message_lowercase:
                case "help":
                    action = print_help()
                case "info":
                    action = print_info()
                case _ if message_lowercase in [
                    "greetings", "hallo", "hello", "hey",
                    "hi", "hola", "holla", "hollo"]:
                    action = (
                        "Greeting!\n"
                        "I'm Slixfeed, an RSS News Bot!\n"
                        "Send \"help\" for instructions."
                        )
                    # print("task_manager[jid]")
                    # print(task_manager[jid])
                    await self.get_roster()
                    print("roster 1")
                    print(self.client_roster)
                    print("roster 2")
                    print(self.client_roster.keys())
                case _ if message_lowercase.startswith("add"):
                    message = message[4:]
                    url = message.split(" ")[0]
                    title = " ".join(message.split(" ")[1:])
                    if url.startswith("http"):
                        action = await filehandler.initdb(
                            jid,
                            datahandler.add_feed_no_check,
                            [url, title]
                            )
                        await taskhandler.refresh_task(
                            self,
                            jid,
                            taskhandler.send_status,
                            "status",
                            20
                            )
                    else:
                        action = "Missing URL."
                case _ if message_lowercase.startswith("allow"):
                        key = "filter-" + message[:5]
                        val = message[6:]
                        if val:
                            keywords = await filehandler.initdb(
                                jid,
                                sqlitehandler.get_settings_value,
                                key
                                )
                            val = await filterhandler.set_filter(
                                val,
                                keywords
                                )
                            await filehandler.initdb(
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
                            keywords = await filehandler.initdb(
                                jid,
                                sqlitehandler.get_settings_value,
                                key
                                )
                            val = await filterhandler.set_filter(
                                val,
                                keywords
                                )
                            await filehandler.initdb(
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
                case _ if (message_lowercase.startswith("gemini") or
                           message_lowercase.startswith("gopher:")):
                    action = "Gemini and Gopher are not supported yet."
                case _ if (message_lowercase.startswith("http") or
                           message_lowercase.startswith("feed:")):
                    url = message
                    if url.startswith("feed:"):
                        url = await datahandler.feed_to_http(url)
                    action = await filehandler.initdb(
                        jid,
                        datahandler.add_feed,
                        url
                        )
                    # action = "> " + message + "\n" + action
                    # FIXME Make the taskhandler to update status message
                    # await taskhandler.refresh_task(
                    #     self,
                    #     jid,
                    #     taskhandler.send_status,
                    #     "status",
                    #     20
                    #     )
                    # NOTE This would show the number of new unread entries
                    await taskhandler.clean_tasks_xmpp(
                        jid,
                        ["status"]
                        )
                    # await taskhandler.send_status(jid)
                    await taskhandler.start_tasks_xmpp(
                        self,
                        jid,
                        ["status"]
                        )
                case _ if message_lowercase.startswith("feeds"):
                    query = message[6:]
                    if query:
                        if len(query) > 3:
                            action = await filehandler.initdb(
                                jid,
                                sqlitehandler.search_feeds,
                                query
                                )
                        else:
                            action = (
                                "Enter at least 4 characters to search"
                                )
                    else:
                        action = await filehandler.initdb(
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
                        await filehandler.initdb(
                            jid,
                            sqlitehandler.set_settings_value,
                            [key, val]
                            )
                        await taskhandler.refresh_task(
                            self,
                            jid,
                            taskhandler.send_update,
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
                    await taskhandler.clean_tasks_xmpp(
                        jid,
                        ["interval", "status"]
                        )
                    await taskhandler.start_tasks_xmpp(
                        self,
                        jid,
                        ["interval", "status"]
                        )
                    # await taskhandler.refresh_task(
                    #     self,
                    #     jid,
                    #     taskhandler.send_update,
                    #     "interval",
                    #     num
                    #     )
                    # await taskhandler.refresh_task(
                    #     self,
                    #     jid,
                    #     taskhandler.send_status,
                    #     "status",
                    #     20
                    #     )
                    # await taskhandler.refresh_task(jid, key, val)
                case _ if message_lowercase.startswith("quantum"):
                    key = message[:7]
                    val = message[8:]
                    if val:
                        # action = (
                        #     "Every update will contain {} news items."
                        #     ).format(action)
                        await filehandler.initdb(
                            jid,
                            sqlitehandler.set_settings_value,
                            [key, val]
                            )
                        action = (
                            "Next update will contain {} news items."
                            ).format(val)
                    else:
                        action = "Missing value."
                case "random":
                    action = "Updates will be sent randomly."
                case _ if message_lowercase.startswith("read"):
                    url = message[5:]
                    if url.startswith("http"):
                        # action = await datahandler.view_feed(url)
                        action = await filehandler.initdb(
                            jid,
                            datahandler.view_feed,
                            url
                            )
                    else:
                        action = "Missing URL."
                case _ if message_lowercase.startswith("recent"):
                    num = message[7:]
                    if num:
                        action = await filehandler.initdb(
                            jid,
                            sqlitehandler.last_entries,
                            num
                            )
                    else:
                        action = "Missing value."
                case _ if message_lowercase.startswith("remove"):
                    ix = message[7:]
                    if ix:
                        action = await filehandler.initdb(
                            jid,
                            sqlitehandler.remove_feed,
                            ix
                            )
                        # await taskhandler.refresh_task(
                        #     self,
                        #     jid,
                        #     taskhandler.send_status,
                        #     "status",
                        #     20
                        #     )
                        await taskhandler.clean_tasks_xmpp(
                            jid,
                            ["status"]
                            )
                        await taskhandler.start_tasks_xmpp(
                            self,
                            jid,
                            ["status"]
                            )
                    else:
                        action = "Missing feed ID."
                case _ if message_lowercase.startswith("search"):
                    query = message[7:]
                    if query:
                        if len(query) > 1:
                            action = await filehandler.initdb(
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
                    await filehandler.initdb(
                        jid,
                        sqlitehandler.set_settings_value,
                        [key, val]
                        )
                    # asyncio.create_task(taskhandler.task_jid(self, jid))
                    await taskhandler.start_tasks_xmpp(
                        self,
                        jid,
                        ["interval", "status", "check"]
                        )
                    action = "Updates are enabled."
                    # print(await datetimehandler.current_time(), "task_manager[jid]")
                    # print(task_manager[jid])
                case "stats":
                    action = await filehandler.initdb(
                        jid,
                        sqlitehandler.statistics
                        )
                case _ if message_lowercase.startswith("select"):
                    num = message[7:]
                    if num:
                        action = await filehandler.initdb(
                            jid,
                            datahandler.view_entry,
                            num
                            )
                    else:
                        action = "Missing number."
                case _ if message_lowercase.startswith("status "):
                    ix = message[7:]
                    action = await filehandler.initdb(
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
                    #     action = await filehandler.initdb(
                    #         jid,
                    #         sqlitehandler.set_settings_value,
                    #         [key, val]
                    #         )
                    # except:
                    #     action = "Updates are already disabled."
                    #     # print("Updates are already disabled. Nothing to do.")
                    # # await taskhandler.send_status(jid)
                    key = "enabled"
                    val = 0
                    await filehandler.initdb(
                        jid,
                        sqlitehandler.set_settings_value,
                        [key, val]
                        )
                    await taskhandler.clean_tasks_xmpp(jid, ["interval"])
                    self.send_presence(
                        pshow="xa",
                        pstatus="Send \"Start\" to receive news.",
                        pto=jid,
                        )
                    action = "Updates are disabled."
                case "support":
                    # TODO Send an invitation.
                    action = "Join xmpp:slixmpp@muc.poez.io?join"
                case _:
                    action = (
                        "Unknown command. "
                        "Press \"help\" for list of commands"
                        )
            if action: msg.reply(action).send()


def print_info():
    """
    Print information.

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
        "THANKS\n"
        " Christian Dersch (SalixOS),"
        " Cyrille Pontvieux (SalixOS, France),"
        "\n"
        " Denis Fomin (Gajim, Russia),"
        " Dimitris Tzemos (SalixOS, Greece),"
        "\n"
        " Emmanuel Gil Peyrot (poezio, France),"
        " George Vlahavas (SalixOS, Greece),"
        "\n"
        " Pierrick Le Brun (SalixOS, France),"
        " Thorsten Mühlfelder (SalixOS, Germany),"
        "\n"
        " Yann Leboulanger (Gajim, France).\n"
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
        "```"
        )
    return msg


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
        " URL\n"
        "   Add URL to subscription list.\n"
        " add URL TITLE\n"
        "   Add URL to subscription list (without validity check).\n"
        " feeds\n"
        "   List subscriptions.\n"
        " interval N\n"
        "   Set interval update to every N minutes.\n"
        " next N\n"
        "   Send N next updates.\n"
        " quantum N\n"
        "   Set amount of updates for each interval.\n"
        " read URL\n"
        "   Display most recent 20 titles of given URL.\n"
        " read URL NUM\n"
        "   Display specified entry from given URL.\n"
        "\n"
        "GROUPCHAT OPTIONS\n"
        " ! (command initiation)\n"
        "   Use exclamation mark to initiate an actionable command.\n"
        " demaster NICKNAME\n"
        "   Remove master privilege.\n"
        " mastership NICKNAME\n"
        "   Add master privilege.\n"
        " ownership NICKNAME\n"
        "   Set new owner.\n"
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
        " help\n"
        "   Print this help manual.\n"
        " info\n"
        "   Print information page.\n"
        " support\n"
        "   Join xmpp:slixmpp@muc.poez.io?join\n"
        # "\n"
        # "PROTOCOLS\n"
        # " Supported prootcols are IRC, Matrix and XMPP.\n"
        # " For the best experience, we recommend you to use XMPP.\n"
        # "\n"
        "```"
        )
    return msg
