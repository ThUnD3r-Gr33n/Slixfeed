#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
from slixfeed.config import Config
import slixfeed.config as config
import slixfeed.sqlite as sqlite
from slixfeed.log import Logger
from slixfeed.xmpp.presence import XmppPresence
import sys

logger = Logger(__name__)


class XmppStatus:


    def send_status_message(self, jid_bare):
        """
        Send status message.
    
        Parameters
        ----------
        jid : str
            Jabber ID.
        """
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid: {}'.format(function_name, jid_bare))
        status_text = '📜️ Slixfeed RSS News Bot'
        db_file = config.get_pathname_to_database(jid_bare)
        enabled = Config.get_setting_value(self.settings, jid_bare, 'enabled')
        if enabled:
            jid_task = self.pending_tasks[jid_bare] if jid_bare in self.pending_tasks else None
            if jid_task and len(jid_task):
                # print('status dnd for ' + jid_bare)
                status_mode = 'dnd'
                status_text = jid_task[list(jid_task.keys())[0]]
            else:
                # print('status enabled for ' + jid_bare)
                feeds = sqlite.get_number_of_items(db_file, 'feeds_properties')
                if not feeds:
                    # print('status no feeds for ' + jid_bare)
                    status_mode = 'available'
                    status_text = '📪️ Send a URL from a blog or a news site'
                else:
                    unread = sqlite.get_number_of_entries_unread(db_file)
                    if unread:
                        # print('status unread for ' + jid_bare)
                        status_mode = 'chat'
                        status_text = '📬️ There are {} news items'.format(str(unread))
                    else:
                        # print('status no news for ' + jid_bare)
                        status_mode = 'available'
                        status_text = '📭️ No news'
        else:
            # print('status disabled for ' + jid_bare)
            status_mode = 'xa'
            status_text = '📪️ Send "Start" to receive updates'
        XmppPresence.send(self, jid_bare, status_text, status_type=status_mode)


class XmppStatusTask:


    async def task_status(self, jid_bare):
        while True:
            XmppStatus.send_status_message(self, jid_bare)
            await asyncio.sleep(60 * 90)


    def restart_task(self, jid_bare):
        if jid_bare == self.boundjid.bare:
            return
        if jid_bare not in self.task_manager:
            self.task_manager[jid_bare] = {}
            logger.info('Creating new task manager for JID {}'.format(jid_bare))
        logger.info('Stopping task "status" for JID {}'.format(jid_bare))
        try:
            self.task_manager[jid_bare]['status'].cancel()
        except:
            logger.info('No task "status" for JID {} (XmppStatusTask.start_task)'
                        .format(jid_bare))
        logger.info('Starting tasks "status" for JID {}'.format(jid_bare))
        self.task_manager[jid_bare]['status'] = asyncio.create_task(
            XmppStatusTask.task_status(self, jid_bare))


        def stop_task(self, jid_bare):
            if (jid_bare in self.task_manager and
                'status' in self.task_manager[jid_bare]):
                self.task_manager[jid_bare]['status'].cancel()
            else:
                logger.debug('No task "status" for JID {}'
                             .format(jid_bare))