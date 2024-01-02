#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

TODO

1) Deprecate "add" (see above) and make it interactive.
   Slixfeed: Do you still want to add this URL to subscription list?
   See: case _ if message_lowercase.startswith("add"):

2) If subscription is inadequate (see state.request), send a message that says so.

    elif not self.client_roster[jid]["to"]:
        breakpoint()
        message.reply("Share online status to activate bot.").send()
        return

"""

import os
from slixfeed.config import (
    add_to_list,
    get_default_dbdir,
    get_value,
    get_pathname_to_database,
    remove_from_list)
from slixfeed.datetime import current_time
import slixfeed.fetch as fetcher
import slixfeed.sqlite as sqlite
import slixfeed.task as task
import slixfeed.utility as utility
import slixfeed.url as uri
import slixfeed.xmpp.bookmark as bookmark
import slixfeed.xmpp.compose as compose
import slixfeed.xmpp.muc as groupchat
import slixfeed.xmpp.status as status
import slixfeed.xmpp.text as text


async def event(self, event):
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

    # Deprecated in favour of event "presence_available"
    # if not main_task:
    #     await select_file()


async def message(self, message):
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

        # await compose.message(self, jid, message)

        message_text = " ".join(message["body"].split())
        if message["type"] == "groupchat":
            message_text = message_text[1:]
        message_lowercase = message_text.lower()
    
        print(current_time(), "ACCOUNT: " + str(message["from"]))
        print(current_time(), "COMMAND:", message_text)
    
        match message_lowercase:
            case "breakpoint":
                breakpoint()
            case "commands":
                response = text.print_cmd()
                send_reply_message(self, message, response)
            case "help":
                response = text.print_help()
                send_reply_message(self, message, response)
            case "info":
                response = text.print_info()
                send_reply_message(self, message, response)
            case _ if message_lowercase in [
                "greetings", "hallo", "hello", "hey",
                "hi", "hola", "holla", "hollo"]:
                response = (
                    "Greeting!\n"
                    "I'm Slixfeed, an RSS News Bot!\n"
                    "Send \"help\" for instructions.\n"
                    )
                send_reply_message(self, message, response)
                # print("task_manager[jid]")
                # print(task_manager[jid])
                await self.get_roster()
                print("roster 1")
                print(self.client_roster)
                print("roster 2")
                print(self.client_roster.keys())
                print("jid")
                print(jid)
    
            # case _ if message_lowercase.startswith("activate"):
            #     if message["type"] == "groupchat":
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
            #             response = "{}, your are in command.".format(nick)
            #         else:
            #             response = "Activation code is not valid."
            #     else:
            #         response = "This command is valid for groupchat only."
            case _ if message_lowercase.startswith("add"):
                message_text = message_text[4:]
                url = message_text.split(" ")[0]
                title = " ".join(message_text.split(" ")[1:])
                if url.startswith("http"):
                    db_file = get_pathname_to_database(jid)
                    response = await fetcher.add_feed_no_check(db_file, [url, title])
                    old = await sqlite.get_settings_value(db_file, "old")
                    if old:
                        await task.clean_tasks_xmpp(jid, ["status"])
                        # await send_status(jid)
                        await task.start_tasks_xmpp(self, jid, ["status"])
                    else:
                        db_file = get_pathname_to_database(jid)
                        await sqlite.mark_source_as_read(db_file, url)
                else:
                    response = "Missing URL."
                send_reply_message(self, message, response)
            case _ if message_lowercase.startswith("allow +"):
                    key = "filter-" + message_text[:5]
                    val = message_text[7:]
                    if val:
                        db_file = get_pathname_to_database(jid)
                        keywords = await sqlite.get_filters_value(db_file, key)
                        val = await add_to_list(val, keywords)
                        await sqlite.set_filters_value(db_file, [key, val])
                        response = (
                            "Approved keywords\n"
                            "```\n{}\n```"
                            ).format(val)
                    else:
                        response = "Missing keywords."
                    send_reply_message(self, message, response)
            case _ if message_lowercase.startswith("allow -"):
                    key = "filter-" + message_text[:5]
                    val = message_text[7:]
                    if val:
                        db_file = get_pathname_to_database(jid)
                        keywords = await sqlite.get_filters_value(db_file, key)
                        val = await remove_from_list(val, keywords)
                        await sqlite.set_filters_value(db_file, [key, val])
                        response = (
                            "Approved keywords\n"
                            "```\n{}\n```"
                            ).format(val)
                    else:
                        response = "Missing keywords."
                    send_reply_message(self, message, response)
            case _ if message_lowercase.startswith("archive"):
                key = message_text[:7]
                val = message_text[8:]
                if val:
                    try:
                        if int(val) > 500:
                            response = "Value may not be greater than 500."
                        else:
                            db_file = get_pathname_to_database(jid)
                            await sqlite.set_settings_value(db_file, [key, val])
                            response = (
                                "Maximum archived items has been set to {}."
                                ).format(val)
                    except:
                        response = "Enter a numeric value only."
                else:
                    response = "Missing value."
                send_reply_message(self, message, response)
            case _ if message_lowercase.startswith("bookmark - "):
                if jid == get_value("accounts", "XMPP", "operator"):
                    muc_jid = message_text[11:]
                    await bookmark.remove(self, muc_jid)
                    response = (
                        "Groupchat {} has been removed from bookmarks."
                        ).format(muc_jid)
                else:
                    response = (
                        "This action is restricted. "
                        "Type: removing bookmarks."
                        )
                send_reply_message(self, message, response)
            case "bookmarks":
                if jid == get_value("accounts", "XMPP", "operator"):
                    response = await compose.list_bookmarks(self)
                else:
                    response = (
                        "This action is restricted. "
                        "Type: viewing bookmarks."
                        )
                send_reply_message(self, message, response)
            case _ if message_lowercase.startswith("deny +"):
                    key = "filter-" + message_text[:4]
                    val = message_text[6:]
                    if val:
                        db_file = get_pathname_to_database(jid)
                        keywords = await sqlite.get_filters_value(db_file, key)
                        val = await add_to_list(val, keywords)
                        await sqlite.set_filters_value(db_file, [key, val])
                        response = (
                            "Rejected keywords\n"
                            "```\n{}\n```"
                            ).format(val)
                    else:
                        response = "Missing keywords."
                    send_reply_message(self, message, response)
            case _ if message_lowercase.startswith("deny -"):
                    key = "filter-" + message_text[:4]
                    val = message_text[6:]
                    if val:
                        db_file = get_pathname_to_database(jid)
                        keywords = await sqlite.get_filters_value(db_file, key)
                        val = await remove_from_list(val, keywords)
                        await sqlite.set_filters_value(db_file, [key, val])
                        response = (
                            "Rejected keywords\n"
                            "```\n{}\n```"
                            ).format(val)
                    else:
                        response = "Missing keywords."
                    send_reply_message(self, message, response)
            case _ if (message_lowercase.startswith("gemini") or
                        message_lowercase.startswith("gopher:")):
                response = "Gemini and Gopher are not supported yet."
                send_reply_message(self, message, response)
            case _ if (message_lowercase.startswith("http") or
                        message_lowercase.startswith("feed:")):
                url = message_text
                await task.clean_tasks_xmpp(jid, ["status"])
                status_type = "dnd"
                status_message = (
                    "📫️ Processing request to fetch data from {}"
                    ).format(url)
                send_status_message(self, jid, status_type, status_message)
                send_reply_message(self, message, response)
                if url.startswith("feed:"):
                    url = uri.feed_to_http(url)
                # url_alt = await uri.replace_hostname(url, "feed")
                # if url_alt:
                #     url = url_alt
                url = (uri.replace_hostname(url, "feed")) or url
                db_file = get_pathname_to_database(jid)
                response = await fetcher.add_feed(db_file, url)
                await task.start_tasks_xmpp(self, jid, ["status"])
                # response = "> " + message + "\n" + response
                # FIXME Make the taskhandler to update status message
                # await refresh_task(
                #     self,
                #     jid,
                #     send_status,
                #     "status",
                #     20
                #     )
                # NOTE This would show the number of new unread entries
                old = await sqlite.get_settings_value(db_file, "old")
                if old:
                    await task.clean_tasks_xmpp(jid, ["status"])
                    # await send_status(jid)
                    await task.start_tasks_xmpp(self, jid, ["status"])
                else:
                    db_file = get_pathname_to_database(jid)
                    await sqlite.mark_source_as_read(db_file, url)
                send_reply_message(self, message, response)
            case _ if message_lowercase.startswith("feeds"):
                query = message_text[6:]
                if query:
                    if len(query) > 3:
                        db_file = get_pathname_to_database(jid)
                        result = await sqlite.search_feeds(db_file, query)
                        response = compose.list_feeds_by_query(query, result)
                    else:
                        response = (
                            "Enter at least 4 characters to search"
                            )
                else:
                    db_file = get_pathname_to_database(jid)
                    result = await sqlite.get_feeds(db_file)
                    response = compose.list_feeds(result)
                send_reply_message(self, message, response)
            case "goodbye":
                if message["type"] == "groupchat":
                    await groupchat.leave(self, jid)
                else:
                    response = "This command is valid for groupchat only."
                send_reply_message(self, message, response)
            case _ if message_lowercase.startswith("interval"):
            # FIXME
            # The following error occurs only upon first attempt to set interval.
            # /usr/lib/python3.11/asyncio/events.py:73: RuntimeWarning: coroutine 'Slixfeed.send_update' was never awaited
            # self._args = None
            # RuntimeWarning: Enable tracemalloc to get the object allocation traceback
                key = message_text[:8]
                val = message_text[9:]
                if val:
                    # response = (
                    #     "Updates will be sent every {} minutes."
                    #     ).format(response)
                    db_file = get_pathname_to_database(jid)
                    await sqlite.set_settings_value(db_file, [key, val])
                    # NOTE Perhaps this should be replaced
                    # by functions clean and start
                    await task.refresh_task(
                        self, jid, task.send_update, key, val)
                    response = (
                        "Updates will be sent every {} minutes."
                        ).format(val)
                else:
                    response = "Missing value."
                send_reply_message(self, message, response)
            case _ if message_lowercase.startswith("join"):
                muc_jid = uri.check_xmpp_uri(message_text[5:])
                if muc_jid:
                    # TODO probe JID and confirm it's a groupchat
                    await groupchat.join(self, jid, muc_jid)
                    response = (
                        "Joined groupchat {}"
                                ).format(message_text)
                else:
                    response = (
                        "> {}\nXMPP URI is not valid."
                                ).format(message_text)
                send_reply_message(self, message, response)
            case _ if message_lowercase.startswith("length"):
                    key = message_text[:6]
                    val = message_text[7:]
                    if val:
                        try:
                            val = int(val)
                            db_file = get_pathname_to_database(jid)
                            await sqlite.set_settings_value(db_file, [key, val])
                            if val == 0:
                                response = (
                                    "Summary length limit is disabled."
                                    )
                            else:
                                response = (
                                    "Summary maximum length "
                                    "is set to {} characters."
                                    ).format(val)
                        except:
                            response = "Enter a numeric value only."
                    else:
                        response = "Missing value."
            # case _ if message_lowercase.startswith("mastership"):
            #         key = message_text[:7]
            #         val = message_text[11:]
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
            #             response = (
            #                 "Operators\n"
            #                 "```\n{}\n```"
            #                 ).format(val)
            #         else:
            #             response = "Missing value."
                    send_reply_message(self, message, response)
            case "new":
                db_file = get_pathname_to_database(jid)
                sqlite.set_settings_value(db_file, ["old", 0])
                response = (
                    "Only new items of newly added feeds will be sent."
                    )
                send_reply_message(self, message, response)
            # TODO Will you add support for number of messages?
            case "next":
                # num = message_text[5:]
                await task.clean_tasks_xmpp(jid, ["interval", "status"])
                await task.start_tasks_xmpp(self, jid, ["interval", "status"])
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
                db_file = get_pathname_to_database(jid)
                await sqlite.set_settings_value(db_file, ["old", 1])
                response = (
                    "All items of newly added feeds will be sent."
                    )
                send_reply_message(self, message, response)
            case _ if message_lowercase.startswith("quantum"):
                key = message_text[:7]
                val = message_text[8:]
                if val:
                    try:
                        val = int(val)
                        # response = (
                        #     "Every update will contain {} news items."
                        #     ).format(response)
                        db_file = get_pathname_to_database(jid)
                        await sqlite.set_settings_value(db_file, [key, val])
                        response = (
                            "Next update will contain {} news items."
                            ).format(val)
                    except:
                        response = "Enter a numeric value only."
                else:
                    response = "Missing value."
                send_reply_message(self, message, response)
            case "random":
                # TODO /questions/2279706/select-random-row-from-a-sqlite-table
                # NOTE sqlitehandler.get_entry_unread
                response = "Updates will be sent by random order."
                send_reply_message(self, message, response)
            case _ if message_lowercase.startswith("read"):
                data = message_text[5:]
                data = data.split()
                url = data[0]
                await task.clean_tasks_xmpp(jid, ["status"])
                status_type = "dnd"
                status_message = (
                    "📫️ Processing request to fetch data from {}"
                    ).format(url)
                send_status_message(self, jid, status_type, status_message)
                if url.startswith("feed:"):
                    url = uri.feed_to_http(url)
                url = (uri.replace_hostname(url, "feed")) or url
                match len(data):
                    case 1:
                        if url.startswith("http"):
                            response = await fetcher.view_feed(url)
                        else:
                            response = "Missing URL."
                    case 2:
                        num = data[1]
                        if url.startswith("http"):
                            response = await fetcher.view_entry(url, num)
                        else:
                            response = "Missing URL."
                    case _:
                        response = (
                            "Enter command as follows:\n"
                            "`read <url>` or `read <url> <number>`\n"
                            "URL must not contain white space."
                            )
                send_reply_message(self, message, response)
                await task.start_tasks_xmpp(self, jid, ["status"])
            case _ if message_lowercase.startswith("recent"):
                num = message_text[7:]
                if num:
                    try:
                        num = int(num)
                        if num < 1 or num > 50:
                            response = "Value must be ranged from 1 to 50."
                        else:
                            db_file = get_pathname_to_database(jid)
                            result = await sqlite.last_entries(db_file, num)
                            response = compose.list_last_entries(result, num)
                    except:
                        response = "Enter a numeric value only."
                else:
                    response = "Missing value."
                send_reply_message(self, message, response)
            # NOTE Should people be asked for numeric value?
            case _ if message_lowercase.startswith("remove"):
                ix = message_text[7:]
                if ix:
                    db_file = get_pathname_to_database(jid)
                    response = await sqlite.remove_feed(db_file, ix)
                    # await refresh_task(
                    #     self,
                    #     jid,
                    #     send_status,
                    #     "status",
                    #     20
                    #     )
                    await task.clean_tasks_xmpp(jid, ["status"])
                    await task.start_tasks_xmpp(self, jid, ["status"])
                else:
                    response = "Missing feed ID."
                send_reply_message(self, message, response)
            case _ if message_lowercase.startswith("reset"):
                source = message_text[6:]
                await task.clean_tasks_xmpp(jid, ["status"])
                status_type = "dnd"
                status_message = "📫️ Marking entries as read..."
                send_status_message(self, jid, status_type, status_message)
                if source:
                    db_file = get_pathname_to_database(jid)
                    await sqlite.mark_source_as_read(db_file, source)
                    response = (
                        "All entries of {} have been "
                        "marked as read.".format(source)
                        )
                else:
                    db_file = get_pathname_to_database(jid)
                    await sqlite.mark_all_as_read(db_file)
                    response = "All entries have been marked as read."
                send_reply_message(self, message, response)
                await task.start_tasks_xmpp(self, jid, ["status"])
            case _ if message_lowercase.startswith("search"):
                query = message_text[7:]
                if query:
                    if len(query) > 1:
                        db_file = get_pathname_to_database(jid)
                        results = await sqlite.search_entries(db_file, query)
                        response = compose.list_search_results(query, results)
                    else:
                        response = (
                            "Enter at least 2 characters to search"
                            )
                else:
                    response = "Missing search query."
                send_reply_message(self, message, response)
            case "start":
                # response = "Updates are enabled."
                key = "enabled"
                val = 1
                db_file = get_pathname_to_database(jid)
                await sqlite.set_settings_value(db_file, [key, val])
                # asyncio.create_task(task_jid(self, jid))
                await task.start_tasks_xmpp(self, jid, ["interval", "status", "check"])
                response = "Updates are enabled."
                # print(current_time(), "task_manager[jid]")
                # print(task_manager[jid])
                send_reply_message(self, message, response)
            case "stats":
                db_file = get_pathname_to_database(jid)
                result = await sqlite.statistics(db_file)
                response = compose.list_statistics(result)
                send_reply_message(self, message, response)
            case _ if message_lowercase.startswith("status "):
                ix = message_text[7:]
                db_file = get_pathname_to_database(jid)
                response = await sqlite.toggle_status(db_file, ix)
                send_reply_message(self, message, response)
            case "stop":
            # FIXME
            # The following error occurs only upon first attempt to stop.
            # /usr/lib/python3.11/asyncio/events.py:73: RuntimeWarning: coroutine 'Slixfeed.send_update' was never awaited
            # self._args = None
            # RuntimeWarning: Enable tracemalloc to get the object allocation traceback
            # response = "Updates are disabled."
                # try:
                #     # task_manager[jid]["check"].cancel()
                #     # task_manager[jid]["status"].cancel()
                #     task_manager[jid]["interval"].cancel()
                #     key = "enabled"
                #     val = 0
                #     response = await initdb(
                #         jid,
                #         set_settings_value,
                #         [key, val]
                #         )
                # except:
                #     response = "Updates are already disabled."
                #     # print("Updates are already disabled. Nothing to do.")
                # # await send_status(jid)
                key = "enabled"
                val = 0
                db_file = get_pathname_to_database(jid)
                await sqlite.set_settings_value(db_file, [key, val])
                await task.clean_tasks_xmpp(jid, ["interval", "status"])
                response = "Updates are disabled."
                send_reply_message(self, message, response)
                status_type = "xa"
                status_message = "💡️ Send \"Start\" to receive Jabber updates"
                send_status_message(self, jid, status_type, status_message)
            case "support":
                # TODO Send an invitation.
                response = (
                    "Join xmpp:slixfeed@chat.woodpeckersnest.space?join")
                send_reply_message(self, message, response)
            case _ if message_lowercase.startswith("xmpp:"):
                muc_jid = uri.check_xmpp_uri(message_text)
                if muc_jid:
                    # TODO probe JID and confirm it's a groupchat
                    await groupchat.join(self, jid, muc_jid)
                    response = (
                        "Joined groupchat {}"
                                ).format(message_text)
                else:
                    response = (
                        "> {}\nXMPP URI is not valid."
                                ).format(message_text)
                send_reply_message(self, message, response)
            case _:
                response = (
                    "Unknown command. "
                    "Press \"help\" for list of commands"
                    )
                send_reply_message(self, message, response)
        # TODO Use message correction here
        # NOTE This might not be a good idea if
        # commands are sent one close to the next
        # if response: message.reply(response).send()

        log_dir = get_default_dbdir()
        if not os.path.isdir(log_dir):
            os.mkdir(log_dir)
        utility.log_as_markdown(
            current_time(), os.path.join(log_dir, jid),
            jid, message_text)
        utility.log_as_markdown(
            current_time(), os.path.join(log_dir, jid),
            self.boundjid.bare, response)


def send_status_message(self, jid, status_type, status_message):
    self.send_presence(
        pshow=status_type,
        pstatus=status_message,
        pto=jid)


def send_reply_message(self, message, response):
    message.reply(response).send()


# def greet(self, jid, chat_type="chat"):
#     messages = [
#         "Greetings!",
#         "I'm {}, the news anchor.".format(self.nick),
#         "My job is to bring you the latest news "
#         "from sources you provide me with.",
#         "You may always reach me via "
#         "xmpp:{}?message".format(self.boundjid.bare)
#         ]
#     for message in messages:
#         self.send_message(
#             mto=jid,
#             mbody=message,
#             mtype=chat_type
#             )


def greet(self, jid, chat_type="chat"):
    message = (
        "Greetings!\n"
        "I'm {}, the news anchor.\n"
        "My job is to bring you the latest "
        "news from sources you provide me with.\n"
        "You may always reach me via xmpp:{}?message").format(
            self.nick,
            self.boundjid.bare
            )
    self.send_message(
        mto=jid,
        mbody=message,
        mtype=chat_type
        )

