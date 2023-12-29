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

3) Do not send updates when busy or away.
    See https://slixmpp.readthedocs.io/en/latest/event_index.html#term-changed_status

4) XHTTML-IM
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
from slixfeed.config import add_to_list, initdb, get_list, remove_from_list
import slixfeed.fetch as fetcher
from slixfeed.datetime import current_time
import logging
# import os
from random import randrange
import slixmpp
from slixmpp.exceptions import IqError, IqTimeout
import slixfeed.sqlite as sqlite
import slixfeed.task as task
import slixfeed.url as urlfixer
from time import sleep

from slixmpp.plugins.xep_0363.http_upload import FileTooBig, HTTPError, UploadServiceNotFound
# from slixmpp.plugins.xep_0402 import BookmarkStorage, Conference
from slixmpp.plugins.xep_0048.stanza import Bookmarks

import xmltodict
import xml.etree.ElementTree as ET
from lxml import etree

import slixfeed.xmpp.compose as compose
import slixfeed.xmpp.connect as connect
import slixfeed.xmpp.muc as muc
import slixfeed.xmpp.status as status

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
    def __init__(self, jid, password, nick):
        slixmpp.ClientXMPP.__init__(self, jid, password)

        # NOTE
        # The bot works fine when the nickname is hardcoded; or
        # The bot won't join some MUCs when its nickname has brackets
        self.nick = nick
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
        self.add_event_handler("message", self.process_message)
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
        jid = presence["from"].bare
        print("presence_available", jid)
        if jid not in self.boundjid.bare:
            await task.clean_tasks_xmpp(
                jid,
                ["interval", "status", "check"]
                )
            await task.start_tasks_xmpp(
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
            await task.clean_tasks_xmpp(
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
        await muc.join_groupchat(self, inviter, muc_jid)


    async def autojoin_muc(self, event):
        result = await self.plugin['xep_0048'].get_bookmarks()
        bookmarks = result["private"]["bookmarks"]
        conferences = bookmarks["conferences"]
        for conference in conferences:
            if conference["autojoin"]:
                muc_jid = conference["jid"]
                print(current_time(), "Autojoining groupchat", muc_jid)
                self.plugin['xep_0045'].join_muc(
                    muc_jid,
                    self.nick,
                    # If a room password is needed, use:
                    # password=the_room_password,
                    )


    async def on_session_end(self, event):
        print(current_time(), "Session ended. Attempting to reconnect.")
        print(event)
        logging.warning("Session ended. Attempting to reconnect.")
        await connect.recover_connection(self, event)


    async def on_connection_failed(self, event):
        print(current_time(), "Connection failed. Attempting to reconnect.")
        print(event)
        logging.warning("Connection failed. Attempting to reconnect.")
        await connect.recover_connection(self, event)


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
            await task.clean_tasks_xmpp(
                jid,
                ["interval"]
                )
            await task.start_tasks_xmpp(
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
        str
            "chat" or "groupchat.
        """
        try:
            iqresult = await self["xep_0030"].get_info(jid=jid)
            features = iqresult["disco_info"]["features"]
            # identity = iqresult['disco_info']['identities']
            # if 'account' in indentity:
            # if 'conference' in indentity:
            if 'http://jabber.org/protocol/muc' in features:
                return "groupchat"
            # TODO elif <feature var='jabber:iq:gateway'/>
            # NOTE Is it needed? We do not interact with gateways or services
            else:
                return "chat"
        # TODO Test whether this exception is realized
        except IqTimeout as e:
            messages = [
                ("Timeout IQ"),
                ("IQ Stanza:", e),
                ("Jabber ID:", jid)
                ]
            for message in messages:
                print(current_time(), message)
                logging.error(current_time(), message)


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
                    pnick=self.nick
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
                    pnick=self.nick
                    )
                self.send_message(
                    mto=jid,
                    # mtype="headline",
                    msubject="RSS News Bot",
                    mbody=(
                        "Accept subscription request to receive updates."
                        ),
                    mfrom=self.boundjid.bare,
                    mnick=self.nick
                    )
                self.send_presence(
                    pto=jid,
                    pfrom=self.boundjid.bare,
                    # Accept symbol 🉑️ 👍️ ✍
                    pstatus=(
                        "✒️ Accept subscription request to receive updates."
                        ),
                    # ptype="subscribe",
                    pnick=self.nick
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
            pnick=self.nick
            )
        self.send_message(
            mto=jid,
            mbody="You have been unsubscribed."
            )
        self.update_roster(
            jid,
            subscription="remove"
            )


    async def process_message(self, message):
        """
        Process incoming message stanzas. Be aware that this also
        includes MUC messages and error messages. It is usually
        a good practice to check the messages's type before
        processing or sending replies.

        Parameters
        ----------
        message : str
            The received message stanza. See the documentation
            for stanza objects and the Message stanza to see
            how it may be used.
        """
        # print("message")
        # print(message)
        if message["type"] in ("chat", "groupchat", "normal"):
            jid = message["from"].bare
            if message["type"] == "groupchat":
                # nick = message["from"][message["from"].index("/")+1:]
                nick = str(message["from"])
                nick = nick[nick.index("/")+1:]
                if (message['muc']['nick'] == self.nick or
                    not message["body"].startswith("!")):
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
                jid_full = str(message["from"])
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

            await compose.message(self, jid, message)
