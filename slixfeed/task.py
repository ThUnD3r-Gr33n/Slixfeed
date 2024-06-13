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
    <presence from="slixfeed@canchat.org/xAPgJLHtMMHF" xml:lang="en" id="ab35c07b63a444d0a7c0a9a0b272f301" to="slixfeed@canchat.org/xAPgJLHtMMHF"><status>📂 Send a URL from a blog or a news site.</status><x xmlns="vcard-temp:x:update"><photo /></x></presence>
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
import os
import slixfeed.config as config
from slixfeed.log import Logger

logger = Logger(__name__)


class Task:


    def start(self, jid_bare, callback):
        callback(self, jid_bare)


    def stop(self, jid_bare, task):
        if (jid_bare in self.task_manager and
            task in self.task_manager[jid_bare]):
            self.task_manager[jid_bare][task].cancel()
        else:
            logger.debug('No task {} for JID {} (Task.stop)'
                         .format(task, jid_bare))


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
    main_task = []
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
