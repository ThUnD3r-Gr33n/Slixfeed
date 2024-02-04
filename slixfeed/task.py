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
import slixfeed.xmpp.connect as connect
import slixfeed.xmpp.utility as utility
import time

main_task = []
jid_tasker = {}
task_manager = {}
loop = asyncio.get_event_loop()


# def init_tasks(self):
#     global task_ping
#     # if task_ping is None or task_ping.done():
#     #     task_ping = asyncio.create_task(ping(self, jid=None))
#     try:
#         task_ping.cancel()
#     except:
#         logging.info('No ping task to cancel')
#     task_ping = asyncio.create_task(ping(self, jid=None))


def ping_task(self):
    global ping_task
    try:
        ping_task.cancel()
    except:
        logging.info('No ping task to cancel.')
    ping_task = asyncio.create_task(connect.ping(self))


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
async def start_tasks_xmpp(self, jid, tasks=None):
    if jid == self.boundjid.bare:
        return
    try:
        task_manager[jid]
        print('Old details for tasks of {}:\n'.format(jid), task_manager[jid].keys())
    except KeyError as e:
        task_manager[jid] = {}
        logging.info('KeyError:', str(e))
        logging.debug('Creating new task manager for JID {}'.format(jid))
    if not tasks:
        tasks = ['interval', 'status', 'check']
    logging.info('Stopping tasks {} for JID {}'.format(tasks, jid))
    for task in tasks:
        # if task_manager[jid][task]:
        try:
            task_manager[jid][task].cancel()
        except:
            logging.debug('No task {} for JID {} (start_tasks_xmpp)'
                          .format(task, jid))
    logging.info('Starting tasks {} for JID {}'.format(tasks, jid))
    for task in tasks:
        # print("task:", task)
        # print("tasks:")
        # print(tasks)
        # breakpoint()
        match task:
            case 'check':
                task_manager[jid]['check'] = asyncio.create_task(
                    check_updates(jid))
            case "status":
                task_manager[jid]['status'] = asyncio.create_task(
                    send_status(self, jid))
            case 'interval':
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
                        await asyncio.sleep(next_update_time)

                        # print("jid              :", jid, "\n"
                        #       "time             :", time.time(), "\n"
                        #       "last_update_time :", last_update_time, "\n"
                        #       "difference       :", diff, "\n"
                        #       "update interval  :", update_interval, "\n"
                        #       "next_update_time :", next_update_time, "\n"
                        #       )

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
    print('New details for tasks of {}:\n'.format(jid), task_manager[jid])


async def clean_tasks_xmpp(jid, tasks=None):
    if not tasks:
        tasks = ['interval', 'status', 'check']
    logging.info('Stopping tasks {} for JID {}'.format(tasks, jid))
    for task in tasks:
        # if task_manager[jid][task]:
        try:
            task_manager[jid][task].cancel()
        except:
            logging.debug('No task {} for JID {} (clean_tasks_xmpp)'
                          .format(task, jid))


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
    logging.info('Sending a news update to JID {}'.format(jid))
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
            title_f = title_f[0]
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
    logging.info('Sending a status message to JID {}'.format(jid))
    status_text = '📜️ Slixfeed RSS News Bot'
    jid_file = jid.replace('/', '_')
    db_file = get_pathname_to_database(jid_file)
    enabled = (
        await get_settings_value(db_file, "enabled") or
        get_value("settings", "Settings", "enabled")
        )
    if not enabled:
        status_mode = 'xa'
        status_text = '📫️ Send "Start" to receive updates'
    else:
        feeds = await get_number_of_items(db_file, 'feeds')
        # print(await current_time(), jid, "has", feeds, "feeds")
        if not feeds:
            status_mode = 'available'
            status_text = '📪️ Send a URL from a blog or a news website'
        else:
            unread = await get_number_of_entries_unread(db_file)
            if unread:
                status_mode = 'chat'
                status_text = '📬️ There are {} news items'.format(str(unread))
                # status_text = (
                #     "📰 News items: {}"
                #     ).format(str(unread))
                # status_text = (
                #     "📰 You have {} news items"
                #     ).format(str(unread))
            else:
                status_mode = 'available'
                status_text = '📭️ No news'

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
    await refresh_task(self, jid, send_status, 'status', '90')
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
    logging.info('Refreshing task {} for JID {}'.format(callback, jid))
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
            logging.info('No task of type {} to cancel for '
                         'JID {} (refresh_task)'.format(key, jid)
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
    logging.info('Scanning for updates for JID {}'.format(jid))
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
            msg = ('Slixfeed does not work without a database.\n'
                   'To create a database, follow these steps:\n'
                   'Add Slixfeed contact to your roster.\n'
                   'Send a feed to the bot by URL:\n'
                   'https://reclaimthenet.org/feed/')
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


