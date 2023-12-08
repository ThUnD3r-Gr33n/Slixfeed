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

5) XHTTML-IM
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
    MUC: self.nick

2) Extracting attribute using xmltodict.
    import xmltodict
    message = xmltodict.parse(str(message))
    jid = message["message"]["x"]["@jid"]

"""

import asyncio
import logging
# import os
import slixmpp
from slixmpp.exceptions import IqError
from random import randrange
from datahandler import (
    add_feed,
    add_feed_no_check,
    check_xmpp_uri,
    feed_to_http,
    view_entry,
    view_feed
    )
from datetimehandler import current_time
from filehandler import initdb
from listhandler import add_to_list, remove_from_list
from sqlitehandler import (
    get_settings_value,
    set_settings_value,
    mark_source_as_read,
    last_entries,
    list_feeds,
    remove_feed,
    search_feeds,
    statistics,
    toggle_status
    )
from taskhandler import (
    clean_tasks_xmpp,
    start_tasks_xmpp,
    refresh_task,
    send_status,
    send_update
    )
from slixmpp.plugins.xep_0363.http_upload import FileTooBig, HTTPError, UploadServiceNotFound
# from slixmpp.plugins.xep_0402 import BookmarkStorage, Conference
from slixmpp.plugins.xep_0048.stanza import Bookmarks

import xmltodict
import xml.etree.ElementTree as ET
from lxml import etree

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
        self.add_event_handler("session_start", self.autojoin_muc)
        self.add_event_handler("session_resumed", self.autojoin_muc)
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

        self.add_event_handler("groupchat_invite", self.process_muc_invite) # XEP_0045
        self.add_event_handler("groupchat_direct_invite", self.process_muc_invite) # XEP_0249
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
            await clean_tasks_xmpp(
                jid,
                ["interval", "status", "check"]
                )
            await start_tasks_xmpp(
                self,
                jid,
                ["interval", "status", "check"]
                )
            # await task_jid(self, jid)
            # main_task.extend([asyncio.create_task(task_jid(jid))])
            # print(main_task)

    async def stop_tasks(self, presence):
        if not self.boundjid.bare:
            jid = presence["from"].bare
            print(">>> unavailable:", jid)
            await clean_tasks_xmpp(
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

    # async def accept_muc_invite(self, message, ctr=None):
    #     # if isinstance(message, str):
    #     if not ctr:
    #         ctr = message["from"].bare
    #         jid = message['groupchat_invite']['jid']
    #     else:
    #         jid = message
    async def process_muc_invite(self, message):
        # operator muc_chat
        inviter = message["from"].bare
        muc_jid = message['groupchat_invite']['jid']
        await self.join_muc(inviter, muc_jid)


    """
    TODO
    1) Send message to inviter that bot has joined to groupchat.
    2) If groupchat requires captcha, send the consequent message.
    3) If groupchat error is received, send that error message to inviter.
    """
    async def join_muc(self, inviter, muc_jid):
        # token = await initdb(
        #     muc_jid,
        #     get_settings_value,
        #     "token"
        #     )
        # if token != "accepted":
        #     token = randrange(10000, 99999)
        #     await initdb(
        #         muc_jid,
        #         set_settings_value,
        #         ["token", token]
        #     )
        #     self.send_message(
        #         mto=inviter,
        #         mbody=(
        #             "Send activation token {} to groupchat xmpp:{}?join."
        #             ).format(token, muc_jid)
        #         )
        print("muc_jid")
        print(muc_jid)
        self.plugin['xep_0045'].join_muc(
            muc_jid,
            "Slixfeed (RSS News Bot)",
            # If a room password is needed, use:
            # password=the_room_password,
            )

        result = await self.plugin['xep_0048'].get_bookmarks()
        bookmarks = result["private"]["bookmarks"]
        conferences = bookmarks["conferences"]
        print("RESULT")
        print(result)
        print("BOOKMARKS")
        print(bookmarks)
        print("CONFERENCES")
        print(conferences)
        # breakpoint()
        mucs = []
        for conference in conferences:
            jid = conference["jid"]
            mucs.extend([jid])
        if muc_jid not in mucs:
            bookmarks = Bookmarks()
            mucs.extend([muc_jid])
            for muc in mucs:
                bookmarks.add_conference(
                    muc,
                    "Slixfeed (RSS News Bot)",
                    autojoin=True
                    )
            await self.plugin['xep_0048'].set_bookmarks(bookmarks)
        # bookmarks = Bookmarks()
        # await self.plugin['xep_0048'].set_bookmarks(bookmarks)
        # print(await self.plugin['xep_0048'].get_bookmarks())

        # bm = BookmarkStorage()
        # bm.conferences.append(Conference(muc_jid, autojoin=True, nick="Slixfeed (RSS News Bot)"))
        # await self['xep_0402'].publish(bm)


    async def remove_and_leave_muc(self, muc_jid):
        self.send_message(
            mto=muc_jid,
            mbody=(
                "If you need me again, contact me directly at {}\n"
                "Goodbye!"
                ).format(self.boundjid.bare)
            )
        result = await self.plugin['xep_0048'].get_bookmarks()
        bookmarks = result["private"]["bookmarks"]
        conferences = bookmarks["conferences"]
        mucs = []
        for conference in conferences:
            jid = conference["jid"]
            mucs.extend([jid])
        if muc_jid in mucs:
            bookmarks = Bookmarks()
            mucs.remove(muc_jid)
            for muc in mucs:
                bookmarks.add_conference(
                    muc,
                    "Slixfeed (RSS News Bot)",
                    autojoin=True
                    )
            await self.plugin['xep_0048'].set_bookmarks(bookmarks)
        self.plugin['xep_0045'].leave_muc(
            muc_jid,
            "Slixfeed (RSS News Bot)",
            "Goodbye!",
            self.boundjid.bare
            )


    async def autojoin_muc(self, event):
        result = await self.plugin['xep_0048'].get_bookmarks()
        bookmarks = result["private"]["bookmarks"]
        conferences = bookmarks["conferences"]
        for conference in conferences:
            if conference["autojoin"]:
                muc = conference["jid"]
                print(muc)
                self.plugin['xep_0045'].join_muc(
                    muc,
                    "Slixfeed (RSS News Bot)",
                    # If a room password is needed, use:
                    # password=the_room_password,
                    )


    async def on_session_end(self, event):
        print(await current_time(), "Session ended. Attempting to reconnect.")
        print(event)
        logging.warning("Session ended. Attempting to reconnect.")
        await self.recover_connection(event)


    async def on_connection_failed(self, event):
        print(await current_time(), "Connection failed. Attempting to reconnect.")
        print(event)
        logging.warning("Connection failed. Attempting to reconnect.")
        await self.recover_connection(event)


    async def recover_connection(self, event):
        self.connection_attempts += 1
        # if self.connection_attempts <= self.max_connection_attempts:
        #     self.reconnect(wait=5.0)  # wait a bit before attempting to reconnect
        # else:
        #     print(await current_time(),"Maximum connection attempts exceeded.")
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
        await refresh_task(
            self,
            jid,
            send_status,
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
            XML stanza .

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
            await clean_tasks_xmpp(
                jid,
                ["interval"]
                )
            await start_tasks_xmpp(
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
        #     await select_file()


    async def is_muc(self, jid):
        """
        Check whether a JID is of MUC.

        Parameters
        ----------
        jid : str
            Jabber ID.

        Returns
        -------
        boolean
            True or False.
        """
        iqresult = await self["xep_0030"].get_info(jid=jid)
        features = iqresult["disco_info"]["features"]
        # identity = iqresult['disco_info']['identities']
        # if 'account' in indentity:
        # if 'conference' in indentity:
        if 'http://jabber.org/protocol/muc' in features:
            return True
        else:
            return False


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
        if await self.is_muc(jid):
            # Check whether JID is in bookmarks; otherwise, add it.
            print(jid, "is muc")
        else:
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
                    # mtype="headline",
                    msubject="RSS News Bot",
                    mbody="Accept subscription request to receive updates.",
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
                # nick = msg["from"][msg["from"].index("/")+1:]
                nick = str(msg["from"])
                nick = nick[nick.index("/")+1:]
                if (msg['muc']['nick'] == "Slixfeed (RSS News Bot)" or
                    not msg["body"].startswith("!")):
                    return
                # token = await initdb(
                #     jid,
                #     get_settings_value,
                #     "token"
                #     )
                # if token == "accepted":
                #     operator = await initdb(
                #         jid,
                #         get_settings_value,
                #         "masters"
                #         )
                #     if operator:
                #         if nick not in operator:
                #             return
                # approved = False
                jid_full = str(msg["from"])
                role = self.plugin['xep_0045'].get_jid_property(
                    jid,
                    jid_full[jid_full.index("/")+1:],
                    "role")
                if role != "moderator":
                    return
                # if role == "moderator":
                #     approved = True
                # TODO Implement a list of temporary operators
                # Once an operator is appointed, the control would last
                # untile the participant has been disconnected from MUC
                # An operator is a function to appoint non moderators.
                # Changing nickname is fine and consist of no problem.
                # if not approved:
                #     operator = await initdb(
                #         jid,
                #         get_settings_value,
                #         "masters"
                #         )
                #     if operator:
                #         if nick in operator:
                #             approved = True
                # if not approved:
                #     return

            # # Begin processing new JID
            # # Deprecated in favour of event "presence_available"
            # db_dir = get_default_dbdir()
            # os.chdir(db_dir)
            # if jid + ".db" not in os.listdir():
            #     await task_jid(jid)
            message = " ".join(msg["body"].split())
            if msg["type"] == "groupchat":
                message = message[1:]
            message_lowercase = message.lower()

            print(await current_time(), "ACCOUNT: " + str(msg["from"]))
            print(await current_time(), "COMMAND:", message)

            match message_lowercase:
                case "commands":
                    action = print_cmd()
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
                    print("jid")
                    print(jid)
                    await self.autojoin_muc()

                # case _ if message_lowercase.startswith("activate"):
                #     if msg["type"] == "groupchat":
                #         acode = message[9:]
                #         token = await initdb(
                #             jid,
                #             get_settings_value,
                #             "token"
                #             )
                #         if int(acode) == token:
                #             await initdb(
                #                 jid,
                #                 set_settings_value,
                #                 ["masters", nick]
                #                 )
                #             await initdb(
                #                 jid,
                #                 set_settings_value,
                #                 ["token", "accepted"]
                #                 )
                #             action = "{}, your are in command.".format(nick)
                #         else:
                #             action = "Activation code is not valid."
                #     else:
                #         action = "This command is valid for groupchat only."
                case _ if message_lowercase.startswith("add"):
                    message = message[4:]
                    url = message.split(" ")[0]
                    title = " ".join(message.split(" ")[1:])
                    if url.startswith("http"):
                        action = await initdb(
                            jid,
                            add_feed_no_check,
                            [url, title]
                            )
                        old = await initdb(
                            jid,
                            get_settings_value,
                            "old"
                            )
                        if old:
                            await clean_tasks_xmpp(
                                jid,
                                ["status"]
                                )
                            # await send_status(jid)
                            await start_tasks_xmpp(
                                self,
                                jid,
                                ["status"]
                                )
                        else:
                            await initdb(
                                jid,
                                mark_source_as_read,
                                url
                                )
                    else:
                        action = "Missing URL."
                case _ if message_lowercase.startswith("allow +"):
                        key = "filter-" + message[:5]
                        val = message[7:]
                        if val:
                            keywords = await initdb(
                                jid,
                                get_settings_value,
                                key
                                )
                            val = await add_to_list(
                                val,
                                keywords
                                )
                            await initdb(
                                jid,
                                set_settings_value,
                                [key, val]
                                )
                            action = (
                                "Approved keywords\n"
                                "```\n{}\n```"
                                ).format(val)
                        else:
                            action = "Missing keywords."
                case _ if message_lowercase.startswith("allow -"):
                        key = "filter-" + message[:5]
                        val = message[7:]
                        if val:
                            keywords = await initdb(
                                jid,
                                get_settings_value,
                                key
                                )
                            val = await remove_from_list(
                                val,
                                keywords
                                )
                            await initdb(
                                jid,
                                set_settings_value,
                                [key, val]
                                )
                            action = (
                                "Approved keywords\n"
                                "```\n{}\n```"
                                ).format(val)
                        else:
                            action = "Missing keywords."
                case _ if message_lowercase.startswith("archive"):
                    key = message[:7]
                    val = message[8:]
                    if val:
                        if int(val) > 500:
                            action = "Value may not be greater than 500."
                        else:
                            await initdb(
                                jid,
                                set_settings_value,
                                [key, val]
                                )
                            action = (
                                "Maximum archived items has been set to {}."
                                ).format(val)
                    else:
                        action = "Missing value."
                case _ if message_lowercase.startswith("deny +"):
                        key = "filter-" + message[:4]
                        val = message[6:]
                        if val:
                            keywords = await initdb(
                                jid,
                                get_settings_value,
                                key
                                )
                            val = await add_to_list(
                                val,
                                keywords
                                )
                            await initdb(
                                jid,
                                set_settings_value,
                                [key, val]
                                )
                            action = (
                                "Rejected keywords\n"
                                "```\n{}\n```"
                                ).format(val)
                        else:
                            action = "Missing keywords."
                case _ if message_lowercase.startswith("deny -"):
                        key = "filter-" + message[:4]
                        val = message[6:]
                        if val:
                            keywords = await initdb(
                                jid,
                                get_settings_value,
                                key
                                )
                            val = await remove_from_list(
                                val,
                                keywords
                                )
                            await initdb(
                                jid,
                                set_settings_value,
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
                        url = await feed_to_http(url)
                    await clean_tasks_xmpp(
                        jid,
                        ["status"]
                        )
                    task = (
                        "📫️ Processing request to fetch data from {}"
                        ).format(url)
                    process_task_message(self, jid, task)
                    action = await initdb(
                        jid,
                        add_feed,
                        url
                        )
                    await start_tasks_xmpp(
                        self,
                        jid,
                        ["status"]
                        )
                    # action = "> " + message + "\n" + action
                    # FIXME Make the taskhandler to update status message
                    # await refresh_task(
                    #     self,
                    #     jid,
                    #     send_status,
                    #     "status",
                    #     20
                    #     )
                    # NOTE This would show the number of new unread entries
                    old = await initdb(
                        jid,
                        get_settings_value,
                        "old"
                        )
                    if old:
                        await clean_tasks_xmpp(
                            jid,
                            ["status"]
                            )
                        # await send_status(jid)
                        await start_tasks_xmpp(
                            self,
                            jid,
                            ["status"]
                            )
                    else:
                        await initdb(
                            jid,
                            mark_source_as_read,
                            url
                            )
                case _ if message_lowercase.startswith("feeds"):
                    query = message[6:]
                    if query:
                        if len(query) > 3:
                            action = await initdb(
                                jid,
                                search_feeds,
                                query
                                )
                        else:
                            action = (
                                "Enter at least 4 characters to search"
                                )
                    else:
                        action = await initdb(
                            jid,
                            list_feeds
                            )
                case "goodbye":
                    if msg["type"] == "groupchat":
                        await self.remove_and_leave_muc(jid)
                    else:
                        action = "This command is valid for groupchat only."
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
                        await initdb(
                            jid,
                            set_settings_value,
                            [key, val]
                            )
                        # NOTE Perhaps this should be replaced
                        # by functions clean and start
                        await refresh_task(
                            self,
                            jid,
                            send_update,
                            key,
                            val
                            )
                        action = (
                            "Updates will be sent every {} minutes."
                            ).format(val)
                    else:
                        action = "Missing value."
                case _ if message_lowercase.startswith("join"):
                    muc = await check_xmpp_uri(message[5:])
                    if muc:
                        "TODO probe JID and confirm it's a groupchat"
                        await self.join_muc(jid, muc)
                        action = (
                            "Joined groupchat {}"
                                  ).format(message)
                    else:
                        action = (
                            "> {}\nXMPP URI is not valid."
                                  ).format(message)
                case _ if message_lowercase.startswith("length"):
                        key = message[:6]
                        val = message[7:]
                        if val:
                            await initdb(
                                jid,
                                set_settings_value,
                                [key, val]
                                )
                            if val == 0:
                                action = (
                                    "Summary length limit is disabled."
                                    )
                            else:
                                action = (
                                    "Summary maximum length "
                                    "is set to {} characters."
                                    ).format(val)
                        else:
                            action = "Missing value."
                # case _ if message_lowercase.startswith("mastership"):
                #         key = message[:7]
                #         val = message[11:]
                #         if val:
                #             names = await initdb(
                #                 jid,
                #                 get_settings_value,
                #                 key
                #                 )
                #             val = await add_to_list(
                #                 val,
                #                 names
                #                 )
                #             await initdb(
                #                 jid,
                #                 set_settings_value,
                #                 [key, val]
                #                 )
                #             action = (
                #                 "Operators\n"
                #                 "```\n{}\n```"
                #                 ).format(val)
                #         else:
                #             action = "Missing value."
                case "new":
                    await initdb(
                        jid,
                        set_settings_value,
                        ["old", 0]
                        )
                    action = (
                        "Only new items of newly added feeds will be sent."
                        )
                case _ if message_lowercase.startswith("next"):
                    num = message[5:]
                    await clean_tasks_xmpp(
                        jid,
                        ["interval", "status"]
                        )
                    await start_tasks_xmpp(
                        self,
                        jid,
                        ["interval", "status"]
                        )
                    # await refresh_task(
                    #     self,
                    #     jid,
                    #     send_update,
                    #     "interval",
                    #     num
                    #     )
                    # await refresh_task(
                    #     self,
                    #     jid,
                    #     send_status,
                    #     "status",
                    #     20
                    #     )
                    # await refresh_task(jid, key, val)
                case "old":
                    await initdb(
                        jid,
                        set_settings_value,
                        ["old", 1]
                        )
                    action = (
                        "All items of newly added feeds will be sent."
                        )
                case _ if message_lowercase.startswith("quantum"):
                    key = message[:7]
                    val = message[8:]
                    if val:
                        # action = (
                        #     "Every update will contain {} news items."
                        #     ).format(action)
                        await initdb(
                            jid,
                            set_settings_value,
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
                    data = message[5:]
                    data = data.split()
                    url = data[0]
                    task = (
                        "📫️ Processing request to fetch data from {}"
                        ).format(url)
                    process_task_message(self, jid, task)
                    await clean_tasks_xmpp(
                        jid,
                        ["status"]
                        )
                    if url.startswith("feed:"):
                        url = await feed_to_http(url)
                    match len(data):
                        case 1:
                            if url.startswith("http"):
                                action = await view_feed(url)
                            else:
                                action = "Missing URL."
                        case 2:
                            num = data[1]
                            if url.startswith("http"):
                                action = await view_entry(url, num)
                            else:
                                action = "Missing URL."
                        case _:
                            action = (
                                "Enter command as follows:\n"
                                "`read URL` or `read URL NUMBER`\n"
                                "URL must not contain white space."
                                )
                    await start_tasks_xmpp(
                        self,
                        jid,
                        ["status"]
                        )
                case _ if message_lowercase.startswith("recent"):
                    num = message[7:]
                    if num:
                        action = await initdb(
                            jid,
                            last_entries,
                            num
                            )
                    else:
                        action = "Missing value."
                case _ if message_lowercase.startswith("remove"):
                    ix = message[7:]
                    if ix:
                        action = await initdb(
                            jid,
                            remove_feed,
                            ix
                            )
                        # await refresh_task(
                        #     self,
                        #     jid,
                        #     send_status,
                        #     "status",
                        #     20
                        #     )
                        await clean_tasks_xmpp(
                            jid,
                            ["status"]
                            )
                        await start_tasks_xmpp(
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
                            action = await initdb(
                                jid,
                                search_entries,
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
                    await initdb(
                        jid,
                        set_settings_value,
                        [key, val]
                        )
                    # asyncio.create_task(task_jid(self, jid))
                    await start_tasks_xmpp(
                        self,
                        jid,
                        ["interval", "status", "check"]
                        )
                    action = "Updates are enabled."
                    # print(await current_time(), "task_manager[jid]")
                    # print(task_manager[jid])
                case "stats":
                    action = await initdb(
                        jid,
                        statistics
                        )
                case _ if message_lowercase.startswith("status "):
                    ix = message[7:]
                    action = await initdb(
                        jid,
                        toggle_status,
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
                    #     action = await initdb(
                    #         jid,
                    #         set_settings_value,
                    #         [key, val]
                    #         )
                    # except:
                    #     action = "Updates are already disabled."
                    #     # print("Updates are already disabled. Nothing to do.")
                    # # await send_status(jid)
                    key = "enabled"
                    val = 0
                    await initdb(
                        jid,
                        set_settings_value,
                        [key, val]
                        )
                    await clean_tasks_xmpp(
                        jid,
                        ["interval", "status"]
                        )
                    self.send_presence(
                        pshow="xa",
                        pstatus="💡️ Send \"Start\" to receive Jabber news",
                        pto=jid,
                        )
                    action = "Updates are disabled."
                case "support":
                    # TODO Send an invitation.
                    action = "Join xmpp:slixmpp@muc.poez.io?join"
                case _ if message_lowercase.startswith("xmpp:"):
                    muc = await check_xmpp_uri(message)
                    if muc:
                        "TODO probe JID and confirm it's a groupchat"
                        await self.join_muc(jid, muc)
                        action = (
                            "Joined groupchat {}"
                                  ).format(message)
                    else:
                        action = (
                            "> {}\nXMPP URI is not valid."
                                  ).format(message)
                case _:
                    action = (
                        "Unknown command. "
                        "Press \"help\" for list of commands"
                        )
            # TODO Use message correction here
            # NOTE This might not be a good idea if
            # commands are sent one close to the next
            if action: msg.reply(action).send()


def process_task_message(self, jid, task):
    self.send_presence(
        pshow="dnd",
        pstatus=task,
        pto=jid,
        )


def print_info():
    """
    Print information.

    Returns
    -------
    msg : str
        Message.
    """
    msg = (
        "```"
        "\n"
        "ABOUT\n"
        " Slixfeed aims to be an easy to use and fully-featured news\n"
        " aggregator bot for XMPP. It provides a convenient access to Blogs,\n"
        " Fediverse and News websites along with filtering functionality."
        "\n"
        " Slixfeed is primarily designed for XMPP (aka Jabber).\n"
        " Visit https://xmpp.org/software/ for more information.\n"
        "\n"
        " XMPP is the Extensible Messaging and Presence Protocol, a set\n"
        " of open technologies for instant messaging, presence, multi-party\n"
        " chat, voice and video calls, collaboration, lightweight\n"
        " middleware, content syndication, and generalized routing of XML\n"
        " data."
        " Visit https://xmpp.org/about/ for more information on the XMPP\n"
        " protocol."
        " "
        # "PLATFORMS\n"
        # " Supported prootcols are IRC, Matrix, Tox and XMPP.\n"
        # " For the best experience, we recommend you to use XMPP.\n"
        # "\n"
        "FILETYPES\n"
        " Supported filetypes: Atom, RDF, RSS and XML.\n"
        "\n"
        "PROTOCOLS\n"
        " Supported protocols: Dat, FTP, Gemini, Gopher, HTTP and IPFS.\n"
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
        " Florent Le Coz (poezio, France),"
        "\n"
        " George Vlahavas (SalixOS, Greece),"
        " Maxime Buquet (slixmpp, France),"
        "\n"
        " Mathieu Pasquet (slixmpp, France),"
        " Pierrick Le Brun (SalixOS, France),"
        "\n"
        " Remko Tronçon (Swift, Germany),"
        " Thorsten Mühlfelder (SalixOS, Germany),"
        "\n"
        " Yann Leboulanger (Gajim, France).\n"
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
        " You can run Slixfeed on your own computer, server, and\n"
        " even on a Linux phone (i.e. Droidian, Kupfer, Mobian, NixOS,\n"
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
        "```"
        "\n"
        "NAME\n"
        "Slixfeed - News syndication bot for Jabber/XMPP\n"
        "\n"
        "DESCRIPTION\n"
        " Slixfeed is a news aggregator bot for online news feeds.\n"
        " This program is primarily designed for XMPP.\n"
        " For more information, visit https://xmpp.org/software/\n"
        "\n"
        "BASIC USAGE\n"
        " URL\n"
        "   Add URL to subscription list.\n"
        " add URL TITLE\n"
        "   Add URL to subscription list (without validity check).\n"
        " join MUC\n"
        "   Join specified groupchat.\n"
        " read URL\n"
        "   Display most recent 20 titles of given URL.\n"
        " read URL N\n"
        "   Display specified entry number from given URL.\n"
        "\n"
        "MESSAGE OPTIONS\n"
        " interval N\n"
        "   Set interval update to every N minutes.\n"
        " length\n"
        "   Set maximum length of news item description. (0 for no limit)\n"
        " new\n"
        "   Send only new items of newly added feeds.\n"
        " next N\n"
        "   Send N next updates.\n"
        " old\n"
        "   Send all items of newly added feeds.\n"
        " quantum N\n"
        "   Set N amount of updates per interval.\n"
        " start\n"
        "   Enable bot and send updates.\n"
        " stop\n"
        "   Disable bot and stop updates.\n"
        "\n"
        "GROUPCHAT OPTIONS\n"
        " ! (command initiation)\n"
        "   Use exclamation mark to initiate an actionable command.\n"
        # " activate CODE\n"
        # "   Activate and command bot.\n"
        # " demaster NICKNAME\n"
        # "   Remove master privilege.\n"
        # " mastership NICKNAME\n"
        # "   Add master privilege.\n"
        # " ownership NICKNAME\n"
        # "   Set new owner.\n"
        "\n"
        "FILTER OPTIONS\n"
        " allow +\n"
        "   Add keywords to allow (comma separates).\n"
        " allow -\n"
        "   Delete keywords from allow list (comma separates).\n"
        " deny +\n"
        "   Keywords to block (comma separates).\n"
        " deny -\n"
        "   Delete keywords from deny list (comma separates).\n"
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
        " feeds\n"
        "   List all subscriptions.\n"
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
        " commands\n"
        "   Print list of commands.\n"
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


def print_cmd():
    """
    Print list of commands.

    Returns
    -------
    msg : str
        Message.
    """
    msg = (
        "```"
        "\n"
        "!                 : Use exclamation mark to initiate an actionable command (groupchats only).\n"
        "<MUC>             : Join specified groupchat.\n"
        "<URL>             : Add URL to subscription list.\n"
        "add <URL> <TITLE> : Add URL to subscription list (without validity check).\n"
        "allow +           : Add keywords to allow (comma separates).\n"
        "allow -           : Delete keywords from allow list (comma separates).\n"
        "deny +            : Keywords to block (comma separates).\n"
        "deny -            : Delete keywords from deny list (comma separates).\n"
        "feeds             : List all subscriptions.\n"
        "feeds <TEXT>      : Search subscriptions by given keywords.\n"
        "interval N        : Set interval update to every N minutes.\n"
        "join <MUC>        : Join specified groupchat.\n"
        "length            : Set maximum length of news item description. (0 for no limit)\n"
        "new               : Send only new items of newly added feeds.\n"
        "next N            : Send N next updates.\n"
        "old               : Send all items of newly added feeds.\n"
        "quantum N         : Set N amount of updates per interval.\n"
        "read <URL>        : Display most recent 20 titles of given URL.\n"
        "read URL N        : Display specified entry number from given URL.\n"
        "recent N          : List recent N news items (up to 50 items).\n"
        "remove <ID>       : Remove feed from subscription list.\n"
        "search <TEXT>     : Search news items by given keywords.\n"
        "start             : Enable bot and send updates.\n"
        "status <ID>       : Toggle update status of feed.\n"
        "stop              : Disable bot and stop updates.\n"
        "```"
        )
    return msg
