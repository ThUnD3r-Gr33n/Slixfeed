#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

IMPORTANT CONSIDERATION

This file appears to be redundant and may be replaced by a dict handler that
would match task keyword to functions.

Or use it as a class Task

tasks_xmpp_chat =  {"check" : check_updates,
                    "status" : task_status_message,
                    "interval" : task_message}
tasks_xmpp_pubsub =  {"check" : check_updates,
                      "pubsub" : task_pubsub}

TODO

1) Deprecate "add" (see above) and make it interactive.
   Slixfeed: Do you still want to add this URL to subscription list?
   See: case _ if message_lowercase.startswith("add"):

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

"""

TIMEOUT

import signal

def handler(signum, frame):
    print("Timeout!")
    raise Exception("end of time")

# This line will set the alarm for 5 seconds

signal.signal(signal.SIGALRM, handler)
signal.alarm(5)

try:
    # Your command here
    pass 
except Exception as exc:
    print(exc)

"""

import asyncio
import logging
import os
import slixfeed.action as action
import slixfeed.config as config
from slixfeed.config import Config
# from slixfeed.dt import current_time
import slixfeed.sqlite as sqlite
# from xmpp import Slixfeed
from slixfeed.xmpp.presence import XmppPresence
from slixfeed.xmpp.message import XmppMessage
from slixfeed.xmpp.connect import XmppConnect
from slixfeed.xmpp.utility import get_chat_type
import time

# main_task = []
# jid_tasker = {}
# task_manager = {}
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


class Task:

    def start(self, jid_full, tasks=None):
        asyncio.create_task()

    def cancel(self, jid_full, tasks=None):
        pass




def task_ping(self):
    # global task_ping_instance
    try:
        self.task_ping_instance.cancel()
    except:
        logging.info('No ping task to cancel.')
    self.task_ping_instance = asyncio.create_task(XmppConnect.ping(self))


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
async def start_tasks_xmpp_pubsub(self, jid_bare, tasks=None):
    try:
        self.task_manager[jid_bare]
    except KeyError as e:
        self.task_manager[jid_bare] = {}
        logging.debug('KeyError:', str(e))
        logging.info('Creating new task manager for JID {}'.format(jid_bare))
    if not tasks:
        tasks = ['check', 'publish']
    logging.info('Stopping tasks {} for JID {}'.format(tasks, jid_bare))
    for task in tasks:
        # if self.task_manager[jid][task]:
        try:
            self.task_manager[jid_bare][task].cancel()
        except:
            logging.info('No task {} for JID {} (start_tasks_xmpp_chat)'
                         .format(task, jid_bare))
    logging.info('Starting tasks {} for JID {}'.format(tasks, jid_bare))
    for task in tasks:
        match task:
            case 'publish':
                self.task_manager[jid_bare]['publish'] = asyncio.create_task(
                    task_publish(self, jid_bare))
            case 'check':
                self.task_manager[jid_bare]['check'] = asyncio.create_task(
                    check_updates(self, jid_bare))


async def task_publish(self, jid_bare):
    jid_file = jid_bare.replace('/', '_')
    db_file = config.get_pathname_to_database(jid_file)
    if jid_bare not in self.settings:
        Config.add_settings_jid(self.settings, jid_bare, db_file)
    while True:
        await action.xmpp_send_pubsub(self, jid_bare)
        await asyncio.sleep(60 * 180)


async def start_tasks_xmpp_chat(self, jid_bare, tasks=None):
    """
    NOTE
    
    For proper activation of tasks involving task 'interval', it is essential
    to place task 'interval' as the last to start due to await asyncio.sleep()
    which otherwise would postpone tasks that would be set after task 'interval'
    """
    if jid_bare == self.boundjid.bare:
        return
    try:
        self.task_manager[jid_bare]
    except KeyError as e:
        self.task_manager[jid_bare] = {}
        logging.debug('KeyError:', str(e))
        logging.info('Creating new task manager for JID {}'.format(jid_bare))
    if not tasks:
        tasks = ['status', 'check', 'interval']
    logging.info('Stopping tasks {} for JID {}'.format(tasks, jid_bare))
    for task in tasks:
        # if self.task_manager[jid][task]:
        try:
            self.task_manager[jid_bare][task].cancel()
        except:
            logging.info('No task {} for JID {} (start_tasks_xmpp_chat)'
                         .format(task, jid_bare))
    logging.info('Starting tasks {} for JID {}'.format(tasks, jid_bare))
    for task in tasks:
        # print("task:", task)
        # print("tasks:")
        # print(tasks)
        # breakpoint()
        match task:
            case 'check':
                self.task_manager[jid_bare]['check'] = asyncio.create_task(
                    check_updates(self, jid_bare))
            case 'status':
                self.task_manager[jid_bare]['status'] = asyncio.create_task(
                    task_status_message(self, jid_bare))
            case 'interval':
                self.task_manager[jid_bare]['interval'] = asyncio.create_task(
                    task_message(self, jid_bare))
    # for task in self.task_manager[jid].values():
    #     print("task_manager[jid].values()")
    #     print(self.task_manager[jid].values())
    #     print("task")
    #     print(task)
    #     print("jid")
    #     print(jid)
    #     breakpoint()
    #     await task


async def task_status_message(self, jid):
    await action.xmpp_send_status_message(self, jid)
    refresh_task(self, jid, task_status_message, 'status', '90')


async def task_message(self, jid_bare):
    jid_file = jid_bare.replace('/', '_')
    db_file = config.get_pathname_to_database(jid_file)
    if jid_bare not in self.settings:
        Config.add_settings_jid(self.settings, jid_bare, db_file)
    update_interval = Config.get_setting_value(self.settings, jid_bare, 'interval')
    update_interval = 60 * int(update_interval)
    last_update_time = sqlite.get_last_update_time(db_file)
    if last_update_time:
        last_update_time = float(last_update_time)
        diff = time.time() - last_update_time
        if diff < update_interval:
            next_update_time = update_interval - diff
            await asyncio.sleep(next_update_time) # FIXME!

            # print("jid              :", jid, "\n"
            #       "time             :", time.time(), "\n"
            #       "last_update_time :", last_update_time, "\n"
            #       "difference       :", diff, "\n"
            #       "update interval  :", update_interval, "\n"
            #       "next_update_time :", next_update_time, "\n"
            #       )

        # elif diff > val:
        #     next_update_time = val
        await sqlite.update_last_update_time(db_file)
    else:
        await sqlite.set_last_update_time(db_file)
    await action.xmpp_send_message(self, jid_bare)
    refresh_task(self, jid_bare, task_message, 'interval')
    await start_tasks_xmpp_chat(self, jid_bare, ['status'])


def clean_tasks_xmpp_chat(self, jid, tasks=None):
    if not tasks:
        tasks = ['interval', 'status', 'check']
    logging.info('Stopping tasks {} for JID {}'.format(tasks, jid))
    for task in tasks:
        # if self.task_manager[jid][task]:
        try:
            self.task_manager[jid][task].cancel()
        except:
            logging.debug('No task {} for JID {} (clean_tasks_xmpp)'
                          .format(task, jid))


def refresh_task(self, jid_bare, callback, key, val=None):
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
    logging.info('Refreshing task {} for JID {}'.format(callback, jid_bare))
    if not val:
        jid_file = jid_bare.replace('/', '_')
        db_file = config.get_pathname_to_database(jid_file)
        if jid_bare not in self.settings:
            Config.add_settings_jid(self.settings, jid_bare, db_file)
        val = Config.get_setting_value(self.settings, jid_bare, key)
    # if self.task_manager[jid][key]:
    if jid_bare in self.task_manager:
        try:
            self.task_manager[jid_bare][key].cancel()
        except:
            logging.info('No task of type {} to cancel for '
                         'JID {} (refresh_task)'.format(key, jid_bare))
        # self.task_manager[jid][key] = loop.call_at(
        #     loop.time() + 60 * float(val),
        #     loop.create_task,
        #     (callback(self, jid))
        #     # send_update(jid)
        # )
        self.task_manager[jid_bare][key] = loop.create_task(
            wait_and_run(self, callback, jid_bare, val)
        )
        # self.task_manager[jid][key] = loop.call_later(
        #     60 * float(val),
        #     loop.create_task,
        #     send_update(jid)
        # )
        # self.task_manager[jid][key] = send_update.loop.call_at(
        #     send_update.loop.time() + 60 * val,
        #     send_update.loop.create_task,
        #     send_update(jid)
        # )


async def wait_and_run(self, callback, jid_bare, val):
    await asyncio.sleep(60 * float(val))
    await callback(self, jid_bare)


# TODO Take this function out of
# <class 'slixmpp.clientxmpp.ClientXMPP'>
async def check_updates(self, jid_bare):
    """
    Start calling for update check up.

    Parameters
    ----------
    jid : str
        Jabber ID.
    """
    logging.info('Scanning for updates for JID {}'.format(jid_bare))
    while True:
        jid_file = jid_bare.replace('/', '_')
        db_file = config.get_pathname_to_database(jid_file)
        urls = sqlite.get_active_feeds_url(db_file)
        for url in urls:
            await action.scan(self, jid_bare, db_file, url)
            await asyncio.sleep(50)
        val = Config.get_setting_value(self.settings, jid_bare, 'check')
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
ActivityPub, IRC, LXMF, Matrix, Nostr, SMTP, Tox.
"""
async def select_file(self):
    """
    Initiate actions by JID (Jabber ID).
    """
    while True:
        db_dir = config.get_default_data_directory()
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
                if (file.endswith('.db') and
                    not file.endswith('.db-jour.db')):
                    jid = file[:-3]
                    main_task.extend([tg.create_task(self.task_jid(jid))])
                    # main_task = [tg.create_task(self.task_jid(jid))]
                    # self.task_manager.update({jid: tg})
