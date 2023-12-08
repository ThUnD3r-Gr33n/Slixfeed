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
    MUC: self.nick

"""

import asyncio
import logging
import os
import slixmpp

from datahandler import download_updates
from datetimehandler import current_time
from filehandler import initdb, get_default_dbdir
from sqlitehandler import (
    get_entry_unread,
    get_settings_value,
    get_number_of_items,
    get_number_of_entries_unread
    )
# from xmpphandler import Slixfeed
import xmpphandler as xmpphandler

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
    task_manager[jid] = {}
    for task in tasks:
        # print("task:", task)
        # print("tasks:")
        # print(tasks)
        # breakpoint()
        match task:
            case "check":
                task_manager[jid]["check"] = asyncio.create_task(
                    check_updates(jid)
                    )
            case "status":
                task_manager[jid]["status"] = asyncio.create_task(
                    send_status(self, jid)
                    )
            case "interval":
                task_manager[jid]["interval"] = asyncio.create_task(
                    send_update(self, jid)
                    )
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
    for task in tasks:
        # if task_manager[jid][task]:
        try:
            task_manager[jid][task].cancel()
        except:
            print("No task", task, "for JID", jid, "(clean_tasks)")


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
    enabled = await initdb(
        jid,
        get_settings_value,
        "enabled"
    )
    # print(await current_time(), "enabled", enabled, jid)
    if enabled:
        # NOTE Perhaps we want to utilize super with keyword
        # arguments in order to know what tasks to initiate.
        task_manager[jid] = {}
        task_manager[jid]["check"] = asyncio.create_task(
            check_updates(jid)
            )
        task_manager[jid]["status"] = asyncio.create_task(
            send_status(self, jid)
            )
        task_manager[jid]["interval"] = asyncio.create_task(
            send_update(self, jid)
            )
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
    # print(await current_time(), jid, "def send_update")
    """
    Send news items as messages.

    Parameters
    ----------
    jid : str
        Jabber ID.
    num : str, optional
        Number. The default is None.
    """
    # print("Starting send_update()")
    # print(jid)
    new = await initdb(
        jid,
        get_entry_unread,
        num
    )
    if new:
        # TODO Add while loop to assure delivery.
        # print(await current_time(), ">>> ACT send_message",jid)
        if await xmpphandler.Slixfeed.is_muc(self, jid):
            chat_type = "groupchat"
        else:
            chat_type = "chat"
        xmpphandler.Slixfeed.send_message(
            self,
            mto=jid,
            mbody=new,
            mtype=chat_type
        )
    # TODO Do not refresh task before
    # verifying that it was completed.
    await refresh_task(
        self,
        jid,
        send_update,
        "interval"
        )
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
    # print(await current_time(), jid, "def send_status")
    """
    Send status message.

    Parameters
    ----------
    jid : str
        Jabber ID.
    """
    # print(await current_time(), "> SEND STATUS",jid)
    status_text="🤖️ Slixfeed RSS News Bot"
    enabled = await initdb(
        jid,
        get_settings_value,
        "enabled"
    )
    if not enabled:
        status_mode = "xa"
        status_text = "📫️ Send \"Start\" to receive updates"
    else:
        feeds = await initdb(
            jid,
            get_number_of_items,
            "feeds"
        )
        # print(await current_time(), jid, "has", feeds, "feeds")
        if not feeds:
            print(">>> not feeds:", feeds, "jid:", jid)
            status_mode = "available"
            status_text = (
                "📪️ Send a URL from a blog or a news website"
                )
        else:
            unread = await initdb(
                jid,
                get_number_of_entries_unread
            )
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
    xmpphandler.Slixfeed.send_presence(
        self,
        pshow=status_mode,
        pstatus=status_text,
        pto=jid,
        #pfrom=None
        )
    # await asyncio.sleep(60 * 20)
    await refresh_task(
        self,
        jid,
        send_status,
        "status",
        "20"
        )
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
    if not val:
        val = await initdb(
            jid,
            get_settings_value,
            key
            )
    # if task_manager[jid][key]:
    if jid in task_manager:
        try:
            task_manager[jid][key].cancel()
        except:
            print("No task of type", key, "to cancel for JID", jid)
        task_manager[jid][key] = loop.call_at(
            loop.time() + 60 * float(val),
            loop.create_task,
            callback(self, jid)
            # send_update(jid)
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


# TODO Take this function out of
# <class 'slixmpp.clientxmpp.ClientXMPP'>
async def check_updates(jid):
    # print(await current_time(), jid, "def check_updates")
    """
    Start calling for update check up.

    Parameters
    ----------
    jid : str
        Jabber ID.
    """
    while True:
        # print(await current_time(), "> CHCK UPDATE",jid)
        await initdb(jid, download_updates)
        await asyncio.sleep(60 * 90)
        # Schedule to call this function again in 90 minutes
        # loop.call_at(
        #     loop.time() + 60 * 90,
        #     loop.create_task,
        #     self.check_updates(jid)
        # )


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
        db_dir = get_default_dbdir()
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
                    main_task.extend([tg.create_task(self.task_jid(jid))])
                    # main_task = [tg.create_task(self.task_jid(jid))]
                    # task_manager.update({jid: tg})


