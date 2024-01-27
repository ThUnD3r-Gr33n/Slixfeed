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

5) Animate "You have X news items"
    📬️ when sent
    📫️ after sent

NOTE

1) Self presence
    Apparently, it is possible to view self presence.
    This means that there is no need to store presences in order to switch or restore presence.
    check_readiness
    <presence from="slixfeed@canchat.org/xAPgJLHtMMHF" xml:lang="en" id="ab35c07b63a444d0a7c0a9a0b272f301" to="slixfeed@canchat.org/xAPgJLHtMMHF"><status>📂 Send a URL from a blog or a news website.</status><x xmlns="vcard-temp:x:update"><photo /></x></presence>
    JID: self.boundjid.bare
    MUC: self.alias

"""

import asyncio
import logging
import os
import slixfeed.action as action
from slixfeed.config import (
    get_pathname_to_database,
    get_default_data_directory,
    get_value)
# from slixfeed.dt import current_time
from slixfeed.sqlite import (
    delete_archived_entry,
    get_feed_title,
    get_feeds_url,
    get_last_update_time,
    get_number_of_entries_unread,
    get_number_of_items,
    get_settings_value,
    get_unread_entries,
    mark_as_read,
    mark_entry_as_read,
    set_last_update_time,
    update_last_update_time
    )
# from xmpp import Slixfeed
import slixfeed.xmpp.client as xmpp
import slixfeed.xmpp.utility as utility
import time

main_task = []
jid_tasker = {}
task_manager = {}
loop = asyncio.get_event_loop()


"""
FIXME

Tasks don't begin at the same time.

This is noticeable when calling "check" before "status".

await taskhandler.start_tasks(
    self,
    jid,
    ["check", "status"]
    )

"""
async def start_tasks_xmpp(self, jid, tasks):
    logging.debug("Starting tasks {} for JID {}".format(tasks, jid))
    task_manager[jid] = {}
    for task in tasks:
        # print("task:", task)
        # print("tasks:")
        # print(tasks)
        # breakpoint()
        match task:
            case "check":
                task_manager[jid]["check"] = asyncio.create_task(
                    check_updates(jid))
            case "status":
                task_manager[jid]["status"] = asyncio.create_task(
                    send_status(self, jid))
            case "interval":
                jid_file = jid.replace('/', '_')
                db_file = get_pathname_to_database(jid_file)
                update_interval = (
                    await get_settings_value(db_file, "interval") or
                    get_value("settings", "Settings", "interval")
                    )
                update_interval = 60 * int(update_interval)
                last_update_time = await get_last_update_time(db_file)
                if last_update_time:
                    last_update_time = float(last_update_time)
                    diff = time.time() - last_update_time
                    if diff < update_interval:
                        next_update_time = update_interval - diff
                        print("jid              :", jid, "\n"
                              "time             :", time.time(), "\n"
                              "last_update_time :", last_update_time, "\n"
                              "difference       :", diff, "\n"
                              "update interval  :", update_interval, "\n"
                              "next_update_time :", next_update_time, "\n")
                        await asyncio.sleep(next_update_time)
                    # elif diff > val:
                    #     next_update_time = val
                    await update_last_update_time(db_file)
                else:
                    await set_last_update_time(db_file)
                task_manager[jid]["interval"] = asyncio.create_task(
                    send_update(self, jid))
    # for task in task_manager[jid].values():
    #     print("task_manager[jid].values()")
    #     print(task_manager[jid].values())
    #     print("task")
    #     print(task)
    #     print("jid")
    #     print(jid)
    #     breakpoint()
    #     await task


async def clean_tasks_xmpp(jid, tasks):
    logging.debug(
        "Stopping tasks {} for JID {}".format(tasks, jid)
        )
    for task in tasks:
        # if task_manager[jid][task]:
        try:
            task_manager[jid][task].cancel()
        except:
            logging.debug(
                "No task {} for JID {} (clean_tasks)".format(task, jid)
                )


"""
TODO

Rename to "start_tasks"

Pass a list (or dict) of tasks to start

NOTE

Consider callback e.g. Slixfeed.send_status.

Or taskhandler for each protocol or specific taskhandler function.
"""
async def task_jid(self, jid):
    """
    JID (Jabber ID) task manager.

    Parameters
    ----------
    jid : str
        Jabber ID.
    """
    jid_file = jid.replace('/', '_')
    db_file = get_pathname_to_database(jid_file)
    enabled = (
        await get_settings_value(db_file, "enabled") or
        get_value("settings", "Settings", "enabled")
        )
    if enabled:
        # NOTE Perhaps we want to utilize super with keyword
        # arguments in order to know what tasks to initiate.
        task_manager[jid] = {}
        task_manager[jid]["check"] = asyncio.create_task(
            check_updates(jid))
        task_manager[jid]["status"] = asyncio.create_task(
            send_status(self, jid))
        task_manager[jid]["interval"] = asyncio.create_task(
            send_update(self, jid))
        await task_manager[jid]["check"]
        await task_manager[jid]["status"]
        await task_manager[jid]["interval"]
        # tasks_dict = {
        #     "check": check_updates,
        #     "status": send_status,
        #     "interval": send_update
        #         }
        # for task, function in tasks_dict.items():
        #     task_manager[jid][task] = asyncio.create_task(
        #         function(jid)
        #         )
        #     await function
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
        await send_status(self, jid)


async def send_update(self, jid, num=None):
    """
    Send news items as messages.

    Parameters
    ----------
    jid : str
        Jabber ID.
    num : str, optional
        Number. The default is None.
    """
    logging.debug("Sending a news update to JID {}".format(jid))
    jid_file = jid.replace('/', '_')
    db_file = get_pathname_to_database(jid_file)
    enabled = (
        await get_settings_value(db_file, "enabled") or
        get_value("settings", "Settings", "enabled")
        )
    if enabled:
        if not num:
            num = (
                await get_settings_value(db_file, "quantum") or
                get_value("settings", "Settings", "quantum")
                )
        else:
            num = int(num)
        news_digest = []
        results = await get_unread_entries(db_file, num)
        news_digest = ''
        media = None
        chat_type = await utility.get_chat_type(self, jid)
        for result in results:
            ix = result[0]
            title_e = result[1]
            url = result[2]
            enclosure = result[3]
            feed_id = result[4]
            date = result[5]
            title_f = get_feed_title(db_file, feed_id)
            news_digest += action.list_unread_entries(result, title_f)
            # print(db_file)
            # print(result[0])
            # breakpoint()
            await mark_as_read(db_file, ix)

            # Find media
            # if url.startswith("magnet:"):
            #     media = action.get_magnet(url)
            # elif enclosure.startswith("magnet:"):
            #     media = action.get_magnet(enclosure)
            # elif enclosure:
            if enclosure:
                media = enclosure
            else:
                media = await action.extract_image_from_html(url)
            
            if media and news_digest:
                # Send textual message
                xmpp.Slixfeed.send_message(
                    self,
                    mto=jid,
                    mfrom=self.boundjid.bare,
                    mbody=news_digest,
                    mtype=chat_type
                    )
                news_digest = ''
                # Send media
                message = xmpp.Slixfeed.make_message(
                    self,
                    mto=jid,
                    mfrom=self.boundjid.bare,
                    mbody=media,
                    mtype=chat_type
                    )
                message['oob']['url'] = media
                message.send()
                media = None
                
        if news_digest:
            # TODO Add while loop to assure delivery.
            # print(await current_time(), ">>> ACT send_message",jid)
            # NOTE Do we need "if statement"? See NOTE at is_muc.
            if chat_type in ("chat", "groupchat"):
                # TODO Provide a choice (with or without images)
                xmpp.Slixfeed.send_message(
                    self,
                    mto=jid,
                    mfrom=self.boundjid.bare,
                    mbody=news_digest,
                    mtype=chat_type
                    )
        # if media:
        #     # message = xmpp.Slixfeed.make_message(
        #     #     self, mto=jid, mbody=new, mtype=chat_type)
        #     message = xmpp.Slixfeed.make_message(
        #         self, mto=jid, mbody=media, mtype=chat_type)
        #     message['oob']['url'] = media
        #     message.send()
                
        # TODO Do not refresh task before
        # verifying that it was completed.
        await refresh_task(
            self, jid, send_update, "interval")
    # interval = await initdb(
    #     jid,
    #     get_settings_value,
    #     "interval"
    # )
    # task_manager[jid]["interval"] = loop.call_at(
    #     loop.time() + 60 * interval,
    #     loop.create_task,
    #     send_update(jid)
    # )

    # print(await current_time(), "asyncio.get_event_loop().time()")
    # print(await current_time(), asyncio.get_event_loop().time())
    # await asyncio.sleep(60 * interval)

    # loop.call_later(
    #     60 * interval,
    #     loop.create_task,
    #     send_update(jid)
    # )

    # print
    # await handle_event()


async def send_status(self, jid):
    """
    Send status message.

    Parameters
    ----------
    jid : str
        Jabber ID.
    """
    logging.debug(
        "Sending a status message to JID {}".format(jid))
    status_text = "📜️ Slixfeed RSS News Bot"
    jid_file = jid.replace('/', '_')
    db_file = get_pathname_to_database(jid_file)
    enabled = (
        await get_settings_value(db_file, "enabled") or
        get_value("settings", "Settings", "enabled")
        )
    if not enabled:
        status_mode = "xa"
        status_text = "📫️ Send \"Start\" to receive updates"
    else:
        feeds = await get_number_of_items(
            db_file, "feeds")
        # print(await current_time(), jid, "has", feeds, "feeds")
        if not feeds:
            status_mode = "available"
            status_text = (
                "📪️ Send a URL from a blog or a news website"
                )
        else:
            unread = await get_number_of_entries_unread(db_file)
            if unread:
                status_mode = "chat"
                status_text = (
                    "📬️ There are {} news items"
                    ).format(str(unread))
                # status_text = (
                #     "📰 News items: {}"
                #     ).format(str(unread))
                # status_text = (
                #     "📰 You have {} news items"
                #     ).format(str(unread))
            else:
                status_mode = "available"
                status_text = "📭️ No news"

    # breakpoint()
    # print(await current_time(), status_text, "for", jid)
    xmpp.Slixfeed.send_presence(
        self,
        pto=jid,
        pfrom=self.boundjid.bare,
        pshow=status_mode,
        pstatus=status_text
        )
    # await asyncio.sleep(60 * 20)
    await refresh_task(
        self, jid, send_status, "status", "20")
    # loop.call_at(
    #     loop.time() + 60 * 20,
    #     loop.create_task,
    #     send_status(jid)
    # )


async def refresh_task(self, jid, callback, key, val=None):
    """
    Apply new setting at runtime.

    Parameters
    ----------
    jid : str
        Jabber ID.
    key : str
        Key.
    val : str, optional
        Value. The default is None.
    """
    logging.debug(
        "Refreshing task {} for JID {}".format(callback, jid)
        )
    if not val:
        jid_file = jid.replace('/', '_')
        db_file = get_pathname_to_database(jid_file)
        val = (
            await get_settings_value(db_file, key) or
            get_value("settings", "Settings", key)
            )
    # if task_manager[jid][key]:
    if jid in task_manager:
        try:
            task_manager[jid][key].cancel()
        except:
            logging.debug(
                "No task of type {} to cancel for "
                "JID {} (clean_tasks)".format(key, jid)
                )
        # task_manager[jid][key] = loop.call_at(
        #     loop.time() + 60 * float(val),
        #     loop.create_task,
        #     (callback(self, jid))
        #     # send_update(jid)
        # )
        task_manager[jid][key] = loop.create_task(
            wait_and_run(self, callback, jid, val)
        )
        # task_manager[jid][key] = loop.call_later(
        #     60 * float(val),
        #     loop.create_task,
        #     send_update(jid)
        # )
        # task_manager[jid][key] = send_update.loop.call_at(
        #     send_update.loop.time() + 60 * val,
        #     send_update.loop.create_task,
        #     send_update(jid)
        # )


async def wait_and_run(self, callback, jid, val):
    await asyncio.sleep(60 * float(val))
    await callback(self, jid)


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
    logging.debug(
        "Scanning for updates for JID {}".format(jid)
        )
    while True:
        jid_file = jid.replace('/', '_')
        db_file = get_pathname_to_database(jid_file)
        urls = await get_feeds_url(db_file)
        for url in urls:
            await action.scan(db_file, url)
        val = get_value(
            "settings", "Settings", "check")
        await asyncio.sleep(60 * float(val))
        # Schedule to call this function again in 90 minutes
        # loop.call_at(
        #     loop.time() + 60 * 90,
        #     loop.create_task,
        #     self.check_updates(jid)
        # )


async def start_tasks(self, presence):
    jid = presence["from"].bare
    logging.debug(
        "Beginning tasks for JID {}".format(jid)
        )
    if jid not in self.boundjid.bare:
        await clean_tasks_xmpp(
            jid, ["interval", "status", "check"]
            )
        await start_tasks_xmpp(
            self, jid, ["interval", "status", "check"]
            )
        # await task_jid(self, jid)
        # main_task.extend([asyncio.create_task(task_jid(jid))])
        # print(main_task)


async def stop_tasks(self, presence):
    if not self.boundjid.bare:
        jid = presence["from"].bare
        logging.debug(
            "Stopping tasks for JID {}".format(jid)
            )
        await clean_tasks_xmpp(
            jid, ["interval", "status", "check"]
            )


async def check_readiness(self, presence):
    """
    Begin tasks if available, otherwise eliminate tasks.

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
        logging.debug(
            "Stopping updates for JID {}".format(jid)
            )
        await clean_tasks_xmpp(
            jid, ["interval"])
        await start_tasks_xmpp(
            self, jid, ["status", "check"])


"""
NOTE
This is an older system, utilizing local storage instead of XMPP presence.
This function is good for use with protocols that might not have presence.
ActivityPub, IRC, LXMF, Matrix, SMTP, Tox.
"""
async def select_file(self):
    """
    Initiate actions by JID (Jabber ID).
    """
    while True:
        db_dir = get_default_data_directory()
        if not os.path.isdir(db_dir):
            msg = (
                "Slixfeed can not work without a database.\n"
                "To create a database, follow these steps:\n"
                "Add Slixfeed contact to your roster.\n"
                "Send a feed to the bot by URL:\n"
                "https://reclaimthenet.org/feed/"
                )
            # print(await current_time(), msg)
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
                if (file.endswith(".db") and
                    not file.endswith(".db-jour.db")):
                    jid = file[:-3]
                    main_task.extend(
                        [tg.create_task(self.task_jid(jid))]
                        )
                    # main_task = [tg.create_task(self.task_jid(jid))]
                    # task_manager.update({jid: tg})


