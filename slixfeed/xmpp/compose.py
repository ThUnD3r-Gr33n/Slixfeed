#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

TODO

1) Deprecate "add" (see above) and make it interactive.
   Slixfeed: Do you still want to add this URL to subscription list?
   See: case _ if message_lowercase.startswith("add"):

"""

from slixfeed.config import add_to_list, initdb, get_list, remove_from_list
from slixfeed.datetime import current_time
import slixfeed.fetch as fetcher
import slixfeed.sqlite as sqlite
import slixfeed.task as task
import slixfeed.url as urlfixer
import slixfeed.xmpp.status as status
import slixfeed.xmpp.text as text

async def message(self, jid, message):
    message_text = " ".join(message["body"].split())
    if message["type"] == "groupchat":
        message_text = message_text[1:]
    message_lowercase = message_text.lower()

    print(current_time(), "ACCOUNT: " + str(message["from"]))
    print(current_time(), "COMMAND:", message_text)

    match message_lowercase:
        case "commands":
            action = text.print_cmd()
        case "help":
            action = text.print_help()
        case "info":
            action = text.print_info()
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
        #             action = "{}, your are in command.".format(nick)
        #         else:
        #             action = "Activation code is not valid."
        #     else:
        #         action = "This command is valid for groupchat only."
        case _ if message_lowercase.startswith("add"):
            message_text = message_text[4:]
            url = message_text.split(" ")[0]
            title = " ".join(message_text.split(" ")[1:])
            if url.startswith("http"):
                action = await initdb(
                    jid,
                    fetcher.add_feed_no_check,
                    [url, title]
                    )
                old = await initdb(
                    jid,
                    sqlite.get_settings_value,
                    "old"
                    )
                if old:
                    await task.clean_tasks_xmpp(
                        jid,
                        ["status"]
                        )
                    # await send_status(jid)
                    await task.start_tasks_xmpp(
                        self,
                        jid,
                        ["status"]
                        )
                else:
                    await initdb(
                        jid,
                        sqlite.mark_source_as_read,
                        url
                        )
            else:
                action = "Missing URL."
        case _ if message_lowercase.startswith("allow +"):
                key = "filter-" + message_text[:5]
                val = message_text[7:]
                if val:
                    keywords = await initdb(
                        jid,
                        sqlite.get_filters_value,
                        key
                        )
                    val = await add_to_list(
                        val,
                        keywords
                        )
                    await initdb(
                        jid,
                        sqlite.set_filters_value,
                        [key, val]
                        )
                    action = (
                        "Approved keywords\n"
                        "```\n{}\n```"
                        ).format(val)
                else:
                    action = "Missing keywords."
        case _ if message_lowercase.startswith("allow -"):
                key = "filter-" + message_text[:5]
                val = message_text[7:]
                if val:
                    keywords = await initdb(
                        jid,
                        sqlite.get_filters_value,
                        key
                        )
                    val = await remove_from_list(
                        val,
                        keywords
                        )
                    await initdb(
                        jid,
                        sqlite.set_filters_value,
                        [key, val]
                        )
                    action = (
                        "Approved keywords\n"
                        "```\n{}\n```"
                        ).format(val)
                else:
                    action = "Missing keywords."
        case _ if message_lowercase.startswith("archive"):
            key = message_text[:7]
            val = message_text[8:]
            if val:
                try:
                    if int(val) > 500:
                        action = "Value may not be greater than 500."
                    else:
                        await initdb(
                            jid,
                            sqlite.set_settings_value,
                            [key, val]
                            )
                        action = (
                            "Maximum archived items has been set to {}."
                            ).format(val)
                except:
                    action = "Enter a numeric value only."
            else:
                action = "Missing value."
        case _ if message_lowercase.startswith("deny +"):
                key = "filter-" + message_text[:4]
                val = message_text[6:]
                if val:
                    keywords = await initdb(
                        jid,
                        sqlite.get_filters_value,
                        key
                        )
                    val = await add_to_list(
                        val,
                        keywords
                        )
                    await initdb(
                        jid,
                        sqlite.set_filters_value,
                        [key, val]
                        )
                    action = (
                        "Rejected keywords\n"
                        "```\n{}\n```"
                        ).format(val)
                else:
                    action = "Missing keywords."
        case _ if message_lowercase.startswith("deny -"):
                key = "filter-" + message_text[:4]
                val = message_text[6:]
                if val:
                    keywords = await initdb(
                        jid,
                        sqlite.get_filters_value,
                        key
                        )
                    val = await remove_from_list(
                        val,
                        keywords
                        )
                    await initdb(
                        jid,
                        sqlite.set_filters_value,
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
            url = message_text
            await task.clean_tasks_xmpp(
                jid,
                ["status"]
                )
            status_message = (
                "📫️ Processing request to fetch data from {}"
                ).format(url)
            status.process_task_message(self, jid, status_message)
            if url.startswith("feed:"):
                url = urlfixer.feed_to_http(url)
            # url_alt = await urlfixer.replace_hostname(url)
            # if url_alt:
            #     url = url_alt
            url = (await urlfixer.replace_hostname(url)) or url
            action = await initdb(
                jid,
                fetcher.add_feed,
                url
                )
            await task.start_tasks_xmpp(
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
                sqlite.get_settings_value,
                "old"
                )
            if old:
                await task.clean_tasks_xmpp(
                    jid,
                    ["status"]
                    )
                # await send_status(jid)
                await task.start_tasks_xmpp(
                    self,
                    jid,
                    ["status"]
                    )
            else:
                await initdb(
                    jid,
                    sqlite.mark_source_as_read,
                    url
                    )
        case _ if message_lowercase.startswith("feeds"):
            query = message_text[6:]
            if query:
                if len(query) > 3:
                    action = await initdb(
                        jid,
                        sqlite.search_feeds,
                        query
                        )
                else:
                    action = (
                        "Enter at least 4 characters to search"
                        )
            else:
                action = await initdb(
                    jid,
                    sqlite.list_feeds
                    )
        case "goodbye":
            if message["type"] == "groupchat":
                await self.close_muc(jid)
            else:
                action = "This command is valid for groupchat only."
        case _ if message_lowercase.startswith("interval"):
        # FIXME
        # The following error occurs only upon first attempt to set interval.
        # /usr/lib/python3.11/asyncio/events.py:73: RuntimeWarning: coroutine 'Slixfeed.send_update' was never awaited
        # self._args = None
        # RuntimeWarning: Enable tracemalloc to get the object allocation traceback
            key = message_text[:8]
            val = message_text[9:]
            if val:
                # action = (
                #     "Updates will be sent every {} minutes."
                #     ).format(action)
                await initdb(
                    jid,
                    sqlite.set_settings_value,
                    [key, val]
                    )
                # NOTE Perhaps this should be replaced
                # by functions clean and start
                await task.refresh_task(
                    self,
                    jid,
                    task.send_update,
                    key,
                    val
                    )
                action = (
                    "Updates will be sent every {} minutes."
                    ).format(val)
            else:
                action = "Missing value."
        case _ if message_lowercase.startswith("join"):
            muc = urlfixer.check_xmpp_uri(message_text[5:])
            if muc:
                "TODO probe JID and confirm it's a groupchat"
                await self.join_muc(jid, muc)
                action = (
                    "Joined groupchat {}"
                            ).format(message_text)
            else:
                action = (
                    "> {}\nXMPP URI is not valid."
                            ).format(message_text)
        case _ if message_lowercase.startswith("length"):
                key = message_text[:6]
                val = message_text[7:]
                if val:
                    try:
                        val = int(val)
                        await initdb(
                            jid,
                            sqlite.set_settings_value,
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
                    except:
                        action = "Enter a numeric value only."
                else:
                    action = "Missing value."
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
        #             action = (
        #                 "Operators\n"
        #                 "```\n{}\n```"
        #                 ).format(val)
        #         else:
        #             action = "Missing value."
        case "new":
            await initdb(
                jid,
                sqlite.set_settings_value,
                ["old", 0]
                )
            action = (
                "Only new items of newly added feeds will be sent."
                )
        # TODO Will you add support for number of messages?
        case "next":
            # num = message_text[5:]
            await task.clean_tasks_xmpp(
                jid,
                ["interval", "status"]
                )
            await task.start_tasks_xmpp(
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
                sqlite.set_settings_value,
                ["old", 1]
                )
            action = (
                "All items of newly added feeds will be sent."
                )
        case _ if message_lowercase.startswith("quantum"):
            key = message_text[:7]
            val = message_text[8:]
            if val:
                try:
                    val = int(val)
                    # action = (
                    #     "Every update will contain {} news items."
                    #     ).format(action)
                    await initdb(
                        jid,
                        sqlite.set_settings_value,
                        [key, val]
                        )
                    action = (
                        "Next update will contain {} news items."
                        ).format(val)
                except:
                    action = "Enter a numeric value only."
            else:
                action = "Missing value."
        case "random":
            # TODO /questions/2279706/select-random-row-from-a-sqlite-table
            # NOTE sqlitehandler.get_entry_unread
            action = "Updates will be sent by random order."
        case _ if message_lowercase.startswith("read"):
            data = message_text[5:]
            data = data.split()
            url = data[0]
            await task.clean_tasks_xmpp(
                jid,
                ["status"]
                )
            status_message = (
                "📫️ Processing request to fetch data from {}"
                ).format(url)
            status.process_task_message(self, jid, status_message)
            if url.startswith("feed:"):
                url = urlfixer.feed_to_http(url)
            url = (await urlfixer.replace_hostname(url)) or url
            match len(data):
                case 1:
                    if url.startswith("http"):
                        action = await fetcher.view_feed(url)
                    else:
                        action = "Missing URL."
                case 2:
                    num = data[1]
                    if url.startswith("http"):
                        action = await fetcher.view_entry(url, num)
                    else:
                        action = "Missing URL."
                case _:
                    action = (
                        "Enter command as follows:\n"
                        "`read <url>` or `read <url> <number>`\n"
                        "URL must not contain white space."
                        )
            await task.start_tasks_xmpp(
                self,
                jid,
                ["status"]
                )
        case _ if message_lowercase.startswith("recent"):
            num = message_text[7:]
            if num:
                try:
                    num = int(num)
                    if num < 1 or num > 50:
                        action = "Value must be ranged from 1 to 50."
                    else:
                        action = await initdb(
                            jid,
                            sqlite.last_entries,
                            num
                            )
                except:
                    action = "Enter a numeric value only."
            else:
                action = "Missing value."
        # NOTE Should people be asked for numeric value?
        case _ if message_lowercase.startswith("remove"):
            ix = message_text[7:]
            if ix:
                action = await initdb(
                    jid,
                    sqlite.remove_feed,
                    ix
                    )
                # await refresh_task(
                #     self,
                #     jid,
                #     send_status,
                #     "status",
                #     20
                #     )
                await task.clean_tasks_xmpp(
                    jid,
                    ["status"]
                    )
                await task.start_tasks_xmpp(
                    self,
                    jid,
                    ["status"]
                    )
            else:
                action = "Missing feed ID."
        case _ if message_lowercase.startswith("reset"):
            source = message_text[6:]
            await task.clean_tasks_xmpp(
                jid,
                ["status"]
                )
            status_message = (
                "📫️ Marking entries as read..."
                )
            status.process_task_message(self, jid, status_message)
            if source:
                await initdb(
                    jid,
                    sqlite.mark_source_as_read,
                    source
                    )
                action = (
                    "All entries of {} have been "
                    "marked as read.".format(source)
                    )
            else:
                await initdb(
                    jid,
                    sqlite.mark_all_as_read
                    )
                action = "All entries have been marked as read."
            await task.start_tasks_xmpp(
                self,
                jid,
                ["status"]
                )
        case _ if message_lowercase.startswith("search"):
            query = message_text[7:]
            if query:
                if len(query) > 1:
                    action = await initdb(
                        jid,
                        sqlite.search_entries,
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
                sqlite.set_settings_value,
                [key, val]
                )
            # asyncio.create_task(task_jid(self, jid))
            await task.start_tasks_xmpp(
                self,
                jid,
                ["interval", "status", "check"]
                )
            action = "Updates are enabled."
            # print(current_time(), "task_manager[jid]")
            # print(task_manager[jid])
        case "stats":
            action = await initdb(
                jid,
                sqlite.statistics
                )
        case _ if message_lowercase.startswith("status "):
            ix = message_text[7:]
            action = await initdb(
                jid,
                sqlite.toggle_status,
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
                sqlite.set_settings_value,
                [key, val]
                )
            await task.clean_tasks_xmpp(
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
            action = "Join xmpp:slixfeed@chat.woodpeckersnest.space?join"
        case _ if message_lowercase.startswith("xmpp:"):
            muc = urlfixer.check_xmpp_uri(message_text)
            if muc:
                "TODO probe JID and confirm it's a groupchat"
                await self.join_muc(jid, muc)
                action = (
                    "Joined groupchat {}"
                            ).format(message_text)
            else:
                action = (
                    "> {}\nXMPP URI is not valid."
                            ).format(message_text)
        case _:
            action = (
                "Unknown command. "
                "Press \"help\" for list of commands"
                )
    # TODO Use message correction here
    # NOTE This might not be a good idea if
    # commands are sent one close to the next
    if action: message.reply(action).send()
