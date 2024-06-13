#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

TODO

1) Deprecate "add" (see above) and make it interactive.
   Slixfeed: Do you still want to add this URL to subscription list?
   See: case _ if command_lowercase.startswith("add"):

2) If subscription is inadequate (see XmppPresence.request), send a message that says so.

    elif not self.client_roster[jid]["to"]:
        breakpoint()
        message.reply("Share online status to activate bot.").send()
        return

3) Set timeout for moderator interaction.
   If moderator interaction has been made, and moderator approves the bot, then
   the bot will add the given groupchat to bookmarks; otherwise, the bot will
   send a message that it was not approved and therefore leaves the groupchat.

"""

import asyncio
from random import randrange # pending_tasks: Use a list and read the first index (i.e. index 0).
import slixfeed.config as config
from slixfeed.config import Config
from slixfeed.log import Logger
import slixfeed.sqlite as sqlite
from slixfeed.url import (
    remove_tracking_parameters,
    replace_hostname,
    )
from slixfeed.syndication import FeedTask
from slixfeed.utilities import Documentation, Html, MD, Task
from slixfeed.xmpp.commands import XmppCommands
from slixfeed.xmpp.message import XmppMessage
from slixfeed.xmpp.presence import XmppPresence
from slixfeed.xmpp.privilege import is_operator, is_moderator
from slixfeed.xmpp.status import XmppStatusTask
from slixfeed.xmpp.upload import XmppUpload
from slixfeed.xmpp.utilities import XmppUtilities
import sys
import time


logger = Logger(__name__)


    # for task in main_task:
    #     task.cancel()

    # Deprecated in favour of event "presence_available"
    # if not main_task:
    #     await select_file()


class XmppChat:


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
        if message['type'] in ('chat', 'groupchat', 'normal'):
            jid_bare = message['from'].bare
            command = ' '.join(message['body'].split())
            command_time_start = time.time()

            # if (message['type'] == 'groupchat' and
            #     message['muc']['nick'] == self.alias):
            #         return

            # FIXME Code repetition. See below.
            # TODO Check alias by nickname associated with conference
            if message['type'] == 'groupchat':
                if (message['muc']['nick'] == self.alias):
                    return
                jid_full = str(message['from'])
                if not is_moderator(self, jid_bare, jid_full):
                    return

            if message['type'] == 'groupchat':
                # nick = message['from'][message['from'].index('/')+1:]
                # nick = str(message['from'])
                # nick = nick[nick.index('/')+1:]
                if (message['muc']['nick'] == self.alias or
                    not message['body'].startswith('!')):
                    return
                # token = await initdb(
                #     jid_bare,
                #     sqlite.get_setting_value,
                #     'token'
                #     )
                # if token == 'accepted':
                #     operator = await initdb(
                #         jid_bare,
                #         sqlite.get_setting_value,
                #         'masters'
                #         )
                #     if operator:
                #         if nick not in operator:
                #             return
                # approved = False
                jid_full = str(message['from'])
                if not is_moderator(self, jid_bare, jid_full):
                    return
                # if role == 'moderator':
                #     approved = True
                # TODO Implement a list of temporary operators
                # Once an operator is appointed, the control would last
                # untile the participant has been disconnected from MUC
                # An operator is a function to appoint non moderators.
                # Changing nickname is fine and consist of no problem.
                # if not approved:
                #     operator = await initdb(
                #         jid_bare,
                #         sqlite.get_setting_value,
                #         'masters'
                #         )
                #     if operator:
                #         if nick in operator:
                #             approved = True
                # if not approved:
                #     return
    
            # # Begin processing new JID
            # # Deprecated in favour of event 'presence_available'
            # db_dir = config.get_default_data_directory()
            # os.chdir(db_dir)
            # if jid + '.db' not in os.listdir():
            #     await task_jid(jid)

            # await compose.message(self, jid_bare, message)

            if message['type'] == 'groupchat':
                command = command[1:]
            command_lowercase = command.lower()

            logger.debug([str(message['from']), ':', command])

            # Support private message via groupchat
            # See https://codeberg.org/poezio/slixmpp/issues/3506
            if message['type'] == 'chat' and message.get_plugin('muc', check=True):
                # jid_bare = message['from'].bare
                jid_full = str(message['from'])
                if (jid_bare == jid_full[:jid_full.index('/')]):
                    # TODO Count and alert of MUC-PM attempts
                    return
    
            response = None
            db_file = config.get_pathname_to_database(jid_bare)
            match command_lowercase:
                case 'help':
                    command_list = XmppCommands.print_help()
                    response = ('Available command keys:\n'
                                '```\n{}\n```\n'
                                'Usage: `help <key>`'
                                .format(command_list))
                case 'help all':
                    command_list = Documentation.manual('commands.toml', section='all')
                    response = ('Complete list of commands:\n'
                                '```\n{}\n```'
                                .format(command_list))
                case _ if command_lowercase.startswith('help'):
                    command = command[5:].lower()
                    command = command.split(' ')
                    if len(command) == 2:
                        command_root = command[0]
                        command_name = command[1]
                        command_list = Documentation.manual(
                            'commands.toml', section=command_root, command=command_name)
                        if command_list:
                            command_list = ''.join(command_list)
                            response = (command_list)
                        else:
                            response = ('KeyError for {} {}'
                                        .format(command_root, command_name))
                    elif len(command) == 1:
                        command = command[0]
                        command_list = Documentation.manual('commands.toml', command)
                        if command_list:
                            command_list = ' '.join(command_list)
                            response = ('Available command `{}` keys:\n'
                                        '```\n{}\n```\n'
                                        'Usage: `help {} <command>`'
                                        .format(command, command_list, command))
                        else:
                            response = 'KeyError for {}'.format(command)
                    else:
                        response = ('Invalid. Enter command key '
                                    'or command key & name')
                case 'info':
                    entries = XmppCommands.print_info_list()
                    response = ('Available command options:\n'
                                '```\n{}\n```\n'
                                'Usage: `info <option>`'
                                .format(entries))
                case _ if command_lowercase.startswith('info'):
                    entry = command[5:].lower()
                    response = XmppCommands.print_info_specific(entry)
                case _ if command_lowercase in ['greetings', 'hallo', 'hello',
                                                'hey', 'hi', 'hola', 'holla',
                                                'hollo']:
                    response = ('Greeting! My name is {}.\n'
                                'I am an RSS News Bot.\n'
                                'Send "help" for further instructions.\n'
                                .format(self.alias))
                case _ if command_lowercase.startswith('add'):
                    command = command[4:]
                    url = command.split(' ')[0]
                    title = ' '.join(command.split(' ')[1:])
                    response = XmppCommands.feed_add(
                        url, db_file, jid_bare, title)
                case _ if command_lowercase.startswith('allow +'):
                        val = command[7:]
                        if val:
                            await XmppCommands.set_filter_allow(
                                db_file, val, True)
                            response = ('Approved keywords\n'
                                        '```\n{}\n```'
                                        .format(val))
                        else:
                            response = ('No action has been taken.'
                                        '\n'
                                        'Missing keywords.')
                case _ if command_lowercase.startswith('allow -'):
                        val = command[7:]
                        if val:
                            await XmppCommands.set_filter_allow(
                                db_file, val, False)
                            response = ('Approved keywords\n'
                                        '```\n{}\n```'
                                        .format(val))
                        else:
                            response = ('No action has been taken.'
                                        '\n'
                                        'Missing keywords.')
                case _ if command_lowercase.startswith('archive'):
                    val = command[8:]
                    if val:
                        response = await XmppCommands.set_archive(
                            self, db_file, jid_bare, val)
                    else:
                        response = 'Current value for archive: '
                        response += XmppCommands.get_archive(self, jid_bare)
                case _ if command_lowercase.startswith('bookmark +'):
                    if is_operator(self, jid_bare):
                        muc_jid = command[11:]
                        response = await XmppCommands.bookmark_add(
                            self, muc_jid)
                    else:
                        response = ('This action is restricted. '
                                    'Type: adding bookmarks.')
                case _ if command_lowercase.startswith('bookmark -'):
                    if is_operator(self, jid_bare):
                        muc_jid = command[11:]
                        response = await XmppCommands.bookmark_del(
                            self, muc_jid)
                    else:
                        response = ('This action is restricted. '
                                    'Type: removing bookmarks.')
                case 'bookmarks':
                    if is_operator(self, jid_bare):
                        response = await XmppCommands.print_bookmarks(self)
                    else:
                        response = ('This action is restricted. '
                                    'Type: viewing bookmarks.')
                case _ if command_lowercase.startswith('clear'):
                    key = command[6:]
                    response = await XmppCommands.clear_filter(db_file, key)
                case _ if command_lowercase.startswith('default'):
                    key = command[8:]
                    response = await XmppCommands.restore_default(
                        self, jid_bare, key=None)
                case 'defaults':
                    response = await XmppCommands.restore_default(self, jid_bare)
                case _ if command_lowercase.startswith('deny +'):
                        val = command[6:]
                        if val:
                            await XmppCommands.set_filter_allow(
                                db_file, val, True)
                            response = ('Rejected keywords\n'
                                        '```\n{}\n```'
                                        .format(val))
                        else:
                            response = ('No action has been taken.'
                                        '\n'
                                        'Missing keywords.')
                case _ if command_lowercase.startswith('deny -'):
                        val = command[6:]
                        if val:
                            await XmppCommands.set_filter_allow(
                                db_file, val, False)
                            response = ('Rejected keywords\n'
                                        '```\n{}\n```'
                                        .format(val))
                        else:
                            response = ('No action has been taken.'
                                        '\n'
                                        'Missing keywords.')
                case _ if command_lowercase.startswith('disable'):
                    response = await XmppCommands.feed_disable(
                        self, db_file, jid_bare, command)
                    XmppStatusTask.restart_task(self, jid_bare)
                case _ if command_lowercase.startswith('enable'):
                    response = await XmppCommands.feed_enable(
                        self, db_file, command)
                case _ if command_lowercase.startswith('export'):
                    ext = command[7:]
                    if ext in ('md', 'opml'): # html xbel
                        status_type = 'dnd'
                        status_message = ('📤️ Procesing request to '
                                          'export feeds into {}...'
                                          .format(ext.upper()))
                        # pending_tasks_num = len(self.pending_tasks[jid_bare])
                        pending_tasks_num = randrange(10000, 99999)
                        self.pending_tasks[jid_bare][pending_tasks_num] = status_message
                        # self.pending_tasks_counter += 1
                        # self.pending_tasks[jid_bare][self.pending_tasks_counter] = status_message
                        XmppPresence.send(self, jid_bare, status_message,
                                          status_type=status_type)
                        filename, response = XmppCommands.export_feeds(
                            self, jid_bare, ext)
                        url = await XmppUpload.start(self, jid_bare, filename)
                        # response = (
                        #     'Feeds exported successfully to {}.\n{}'
                        #     ).format(ex, url)
                        # XmppMessage.send_oob_reply_message(message, url, response)
                        chat_type = await XmppUtilities.get_chat_type(self, jid_bare)
                        XmppMessage.send_oob(self, jid_bare, url, chat_type)
                        del self.pending_tasks[jid_bare][pending_tasks_num]
                        # del self.pending_tasks[jid_bare][self.pending_tasks_counter]
                        XmppStatusTask.restart_task(self, jid_bare)
                    else:
                        response = ('Unsupported filetype.\n'
                                    'Try: md or opml')
                case _ if command_lowercase.startswith('feeds'):
                    query = command[6:]
                    result, number = XmppCommands.list_feeds(db_file, query)
                    if number:
                        if query:
                            first_line = 'Subscriptions containing "{}":\n\n```\n'.format(query)
                        else:
                            first_line = 'Subscriptions:\n\n```\n'
                        response = (first_line + result +
                                    '\n```\nTotal of {} feeds'.format(number))
                case 'goodbye':
                    if message['type'] == 'groupchat':
                        await XmppCommands.muc_leave(self, jid_bare)
                    else:
                        response = 'This command is valid in groupchat only.'
                case _ if (command_lowercase.startswith('gemini:') or
                           command_lowercase.startswith('gopher:')):
                    response = XmppCommands.fetch_gemini()
                case _ if (command_lowercase.startswith('http') and
                           command_lowercase.endswith('.opml')):
                    Task.stop(self, jid_bare, 'status')
                    status_type = 'dnd'
                    status_message = '📥️ Procesing request to import feeds...'
                    # pending_tasks_num = len(self.pending_tasks[jid_bare])
                    pending_tasks_num = randrange(10000, 99999)
                    self.pending_tasks[jid_bare][pending_tasks_num] = status_message
                    # self.pending_tasks_counter += 1
                    # self.pending_tasks[jid_bare][self.pending_tasks_counter] = status_message
                    XmppPresence.send(self, jid_bare, status_message,
                                      status_type=status_type)
                    response = await XmppCommands.import_opml(
                        self, db_file, jid_bare, command)
                    del self.pending_tasks[jid_bare][pending_tasks_num]
                    # del self.pending_tasks[jid_bare][self.pending_tasks_counter]
                    XmppStatusTask.restart_task(self, jid_bare)
                case _ if command_lowercase.startswith('pubsub list'):
                    jid = command[12:]
                    response = 'List of nodes for {}:\n```\n'.format(jid)
                    response = await XmppCommands.pubsub_list(self, jid)
                    response += '```'
                case _ if command_lowercase.startswith('pubsub send'):
                    if is_operator(self, jid_bare):
                        info = command[12:]
                        info = info.split(' ')
                        jid = info[0]
                        # num = int(info[1])
                        if jid:
                            response = XmppCommands.pubsub_send(self, info, jid)
                    else:
                        response = ('This action is restricted. '
                                    'Type: sending news to PubSub.')
                # TODO Handle node error
                # sqlite3.IntegrityError: UNIQUE constraint failed: feeds_pubsub.node
                # ERROR:slixmpp.basexmpp:UNIQUE constraint failed: feeds_pubsub.node
                case _ if (command_lowercase.startswith('http') or
                           command_lowercase.startswith('feed:/') or
                           command_lowercase.startswith('itpc:/') or
                           command_lowercase.startswith('rss:/')):
                    url = command
                    status_type = 'dnd'
                    status_message = ('📫️ Processing request to fetch data from {}'
                                      .format(url))
                    # pending_tasks_num = len(self.pending_tasks[jid_bare])
                    pending_tasks_num = randrange(10000, 99999)
                    self.pending_tasks[jid_bare][pending_tasks_num] = status_message
                    # self.pending_tasks_counter += 1
                    # self.pending_tasks[jid_bare][self.pending_tasks_counter] = status_message
                    XmppPresence.send(self, jid_bare, status_message,
                                      status_type=status_type)
                    response = await XmppCommands.fetch_http(
                        self, command, db_file, jid_bare)
                    del self.pending_tasks[jid_bare][pending_tasks_num]
                    # del self.pending_tasks[jid_bare][self.pending_tasks_counter]
                    XmppStatusTask.restart_task(self, jid_bare)
                    # except:
                    #     response = (
                    #         '> {}\nNews source is in the process '
                    #         'of being added to the subscription '
                    #         'list.'.format(url)
                    #         )
                case _ if command_lowercase.startswith('interval'):
                    val = command[9:]
                    if val:
                        response = await XmppCommands.set_interval(
                            self, db_file, jid_bare, val)
                        XmppChatTask.restart_task(self, jid_bare)
                    else:
                        response = 'Current value for interval: '
                        response += XmppCommands.get_interval(self, jid_bare)
                case _ if command_lowercase.startswith('join'):
                    muc_jid = command[5:]
                    response = await XmppCommands.muc_join(self, muc_jid)
                case _ if command_lowercase.startswith('length'):
                        val = command[7:]
                        if val:
                            response = await XmppCommands.set_length(
                                self, db_file, jid_bare, val)
                        else:
                            response = 'Current value for length: '
                            response += XmppCommands.get_length(self, jid_bare)
                case 'media off':
                    response = await XmppCommands.set_media_off(
                        self, jid_bare, db_file)
                case 'media on':
                    response = await XmppCommands.set_media_on(
                        self, jid_bare, db_file)
                case 'new':
                    response = await XmppCommands.set_old_off(
                        self, jid_bare, db_file)
                case _ if command_lowercase.startswith('next'):
                    num = command[5:]
                    await XmppChatAction.send_unread_items(self, jid_bare, num)
                    XmppStatusTask.restart_task(self, jid_bare)
                case _ if command_lowercase.startswith('node delete'):
                    if is_operator(self, jid_bare):
                        info = command[12:]
                        info = info.split(' ')
                        response = XmppCommands.node_delete(self, info)
                    else:
                        response = ('This action is restricted. '
                                    'Type: sending news to PubSub.')
                case _ if command_lowercase.startswith('node purge'):
                    if is_operator(self, jid_bare):
                        info = command[11:]
                        info = info.split(' ')
                        response = XmppCommands.node_purge(self, info)
                    else:
                        response = ('This action is restricted. '
                                    'Type: sending news to PubSub.')
                case 'old':
                    response = await XmppCommands.set_old_on(
                        self, jid_bare, db_file)
                case 'options':
                    response = 'Options:\n```'
                    response += XmppCommands.print_options(self, jid_bare)
                    response += '\n```'
                case _ if command_lowercase.startswith('quantum'):
                    val = command[8:]
                    if val:
                        response = await XmppCommands.set_quantum(
                            self, db_file, jid_bare, val)
                    else:
                        response = 'Current value for quantum: '
                        response += XmppCommands.get_quantum(self, jid_bare)
                case 'random':
                    response = XmppCommands.set_random(self, jid_bare, db_file)
                case _ if command_lowercase.startswith('read'):
                    data = command[5:]
                    data = data.split()
                    url = data[0]
                    if url:
                        Task.stop(self, jid_bare, 'status')
                        status_type = 'dnd'
                        status_message = ('📫️ Processing request to fetch data '
                                          'from {}'.format(url))
                        pending_tasks_num = randrange(10000, 99999)
                        self.pending_tasks[jid_bare][pending_tasks_num] = status_message
                        response = await XmppCommands.feed_read(
                            self, jid_bare, data, url)
                        del self.pending_tasks[jid_bare][pending_tasks_num]
                        XmppStatusTask.restart_task(self, jid_bare)
                    else:
                        response = ('No action has been taken.'
                                    '\n'
                                    'Missing URL.')
                case _ if command_lowercase.startswith('recent'):
                    num = command[7:]
                    if not num: num = 5
                    count, result = XmppCommands.print_recent(self, db_file, num)
                    if count:
                        response = 'Recent {} fetched titles:\n\n```'.format(num)
                        response += result + '```\n'
                    else:
                        response = result
                case _ if command_lowercase.startswith('remove'):
                    ix_url = command[7:]
                    ix_url = ix_url.split(' ')
                    response = await XmppCommands.feed_remove(
                        self, jid_bare, db_file, ix_url)
                    XmppStatusTask.restart_task(self, jid_bare)
                case _ if command_lowercase.startswith('rename'):
                    response = await XmppCommands.feed_rename(
                        self, db_file, jid_bare, command)
                case _ if command_lowercase.startswith('reset'):
                    ix_url = command[6:]
                    if ix_url: ix_url = ix_url.split(' ')
                    Task.stop(self, jid_bare, 'status')
                    status_type = 'dnd'
                    status_message = '📫️ Marking entries as read...'
                    # pending_tasks_num = len(self.pending_tasks[jid_bare])
                    pending_tasks_num = randrange(10000, 99999)
                    self.pending_tasks[jid_bare][pending_tasks_num] = status_message
                    # self.pending_tasks_counter += 1
                    # self.pending_tasks[jid_bare][self.pending_tasks_counter] = status_message
                    XmppPresence.send(self, jid_bare, status_message,
                                      status_type=status_type)
                    response = await XmppCommands.mark_as_read(
                        jid_bare, db_file, ix_url)
                    del self.pending_tasks[jid_bare][pending_tasks_num]
                    # del self.pending_tasks[jid_bare][self.pending_tasks_counter]
                    XmppStatusTask.restart_task(self, jid_bare)
                case _ if command_lowercase.startswith('search'):
                    query = command[7:]
                    response = XmppCommands.search_items(db_file, query)
                case 'start':
                    status_type = 'available'
                    status_message = '📫️ Welcome back!'
                    XmppPresence.send(self, jid_bare, status_message,
                                      status_type=status_type)
                    await asyncio.sleep(5)
                    tasks = (FeedTask, XmppChatTask, XmppStatusTask)
                    response = await XmppCommands.scheduler_start(
                        self, db_file, jid_bare, tasks)
                case 'stats':
                    response = XmppCommands.print_statistics(db_file)
                case 'stop':
                    response = await XmppCommands.scheduler_stop(
                        self, db_file, jid_bare)
                    status_type = 'xa'
                    status_message = '📪️ Send "Start" to receive Jabber updates'
                    XmppPresence.send(self, jid_bare, status_message,
                                      status_type=status_type)
                case 'support':
                    response = XmppCommands.print_support_jid()
                    await XmppCommands.invite_jid_to_muc(self, jid_bare)
                case 'version':
                    response = XmppCommands.print_version(self, jid_bare)
                case _ if command_lowercase.startswith('xmpp:'):
                    response = await XmppCommands.muc_join(self, command)
                case _:
                    response = XmppCommands.print_unknown()
            # TODO Use message correction here
            # NOTE This might not be a good idea if
            # commands are sent one close to the next
            # if response: message.reply(response).send()
    
            command_time_finish = time.time()
            command_time_total = command_time_finish - command_time_start
            command_time_total = round(command_time_total, 3)
            if response: XmppMessage.send_reply(self, message, response)
            if Config.get_setting_value(self.settings, jid_bare, 'finished'):
                response_finished = 'Finished. Total time: {}s'.format(command_time_total)
                XmppMessage.send_reply(self, message, response_finished)

            # if not response: response = 'EMPTY MESSAGE - ACTION ONLY'
            # data_dir = config.get_default_data_directory()
            # if not os.path.isdir(data_dir):
            #     os.mkdir(data_dir)
            # if not os.path.isdir(data_dir + '/logs/'):
            #     os.mkdir(data_dir + '/logs/')
            # MD.log_to_markdown(
            #     dt.current_time(), os.path.join(data_dir, 'logs', jid_bare),
            #     jid_bare, command)
            # MD.log_to_markdown(
            #     dt.current_time(), os.path.join(data_dir, 'logs', jid_bare),
            #     jid_bare, response)
    
            # print(
            #     'Message : {}\n'
            #     'JID     : {}\n'
            #     '{}\n'
            #     .format(command, jid_bare, response)
            #     )


class XmppChatAction:


    async def send_unread_items(self, jid_bare, num=None):
        """
        Send news items as messages.

        Parameters
        ----------
        jid : str
            Jabber ID.
        num : str, optional
            Number. The default is None.
        """
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid: {} num: {}'.format(function_name, jid_bare, num))
        db_file = config.get_pathname_to_database(jid_bare)
        show_media = Config.get_setting_value(self.settings, jid_bare, 'media')
        if not num:
            num = Config.get_setting_value(self.settings, jid_bare, 'quantum')
        else:
            num = int(num)
        results = sqlite.get_unread_entries(db_file, num)
        news_digest = ''
        media = None
        chat_type = await XmppUtilities.get_chat_type(self, jid_bare)
        for result in results:
            ix = result[0]
            title_e = result[1]
            url = result[2]
            summary = result[3]
            feed_id = result[4]
            date = result[5]
            enclosure = sqlite.get_enclosure_by_entry_id(db_file, ix)
            if enclosure: enclosure = enclosure[0]
            title_f = sqlite.get_feed_title(db_file, feed_id)
            title_f = title_f[0]
            news_digest += await XmppChatAction.list_unread_entries(self, result, title_f, jid_bare)
            # print(db_file)
            # print(result[0])
            # breakpoint()
            await sqlite.mark_as_read(db_file, ix)

            # Find media
            # if url.startswith("magnet:"):
            #     media = action.get_magnet(url)
            # elif enclosure.startswith("magnet:"):
            #     media = action.get_magnet(enclosure)
            # elif enclosure:
            if show_media:
                if enclosure:
                    media = enclosure
                else:
                    media = await Html.extract_image_from_html(url)
            
            if media and news_digest:
                # Send textual message
                XmppMessage.send(self, jid_bare, news_digest, chat_type)
                news_digest = ''
                # Send media
                XmppMessage.send_oob(self, jid_bare, media, chat_type)
                media = None
                
        if news_digest:
            XmppMessage.send(self, jid_bare, news_digest, chat_type)
                # TODO Add while loop to assure delivery.
                # print(await current_time(), ">>> ACT send_message",jid)
                # NOTE Do we need "if statement"? See NOTE at is_muc.
                # if chat_type in ('chat', 'groupchat'):
                #     # TODO Provide a choice (with or without images)
                #     XmppMessage.send(self, jid, news_digest, chat_type)
            # See XEP-0367
            # if media:
            #     # message = xmpp.Slixfeed.make_message(
            #     #     self, mto=jid, mbody=new, mtype=chat_type)
            #     message = xmpp.Slixfeed.make_message(
            #         self, mto=jid, mbody=media, mtype=chat_type)
            #     message['oob']['url'] = media
            #     message.send()
                    
            # TODO Do not refresh task before
            # verifying that it was completed.

            # XmppStatusTask.restart_task(self, jid_bare)
            # XmppCommands.task_start(self, jid_bare, 'interval')

        # interval = await initdb(
        #     jid,
        #     sqlite.is_setting_key,
        #     "interval"
        # )
        # self.task_manager[jid]["interval"] = loop.call_at(
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


    async def list_unread_entries(self, result, feed_title, jid):
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: feed_title: {} jid: {}'
                    .format(function_name, feed_title, jid))
        # TODO Add filtering
        # TODO Do this when entry is added to list and mark it as read
        # DONE!
        # results = []
        # if sqlite.is_setting_key(db_file, "deny"):
        #     while len(results) < num:
        #         result = cur.execute(sql).fetchone()
        #         blacklist = sqlite.get_setting_value(db_file, "deny").split(",")
        #         for i in blacklist:
        #             if i in result[1]:
        #                 continue
        #                 print("rejected:", result[1])
        #         print("accepted:", result[1])
        #         results.extend([result])
    
        # news_list = "You've got {} news items:\n".format(num)
        # NOTE Why doesn't this work without list?
        #      i.e. for result in results
        # for result in results.fetchall():
        ix = str(result[0])
        title = str(result[1]) or '*** No title ***' # [No Title]
        # Remove HTML tags
        title = Html.remove_html_tags(title) if title else '*** No title ***'
        # # TODO Retrieve summary from feed
        # # See fetch.view_entry
        summary = result[3]
        if summary:
            summary = Html.remove_html_tags(summary)
            # TODO Limit text length
            # summary = summary.replace("\n\n\n", "\n\n")
            summary = summary.replace('\n', ' ')
            summary = summary.replace('	', ' ')
            # summary = summary.replace('  ', ' ')
            summary = ' '.join(summary.split())
            length = Config.get_setting_value(self.settings, jid, 'length')
            length = int(length)
            summary = summary[:length] + " […]"
            # summary = summary.strip().split('\n')
            # summary = ["> " + line for line in summary]
            # summary = "\n".join(summary)
        else:
            summary = '*** No summary ***'
        link = result[2]
        link = remove_tracking_parameters(link)
        link = await replace_hostname(link, "link") or link
        feed_id = result[4]
        # news_item = ("\n{}\n{}\n{} [{}]\n").format(str(title), str(link),
        #                                            str(feed_title), str(ix))
        formatting = Config.get_setting_value(self.settings, jid, 'formatting')
        news_item = formatting.format(feed_title=feed_title,
                                      title=title,
                                      summary=summary,
                                      link=link,
                                      ix=ix,
                                      feed_id=feed_id)
        # news_item = news_item.replace('\\n', '\n')
        return news_item


class XmppChatTask:


    async def task_message(self, jid_bare):
        db_file = config.get_pathname_to_database(jid_bare)
        if jid_bare not in self.settings:
            Config.add_settings_jid(self.settings, jid_bare, db_file)
        while True:
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
            await XmppChatAction.send_unread_items(self, jid_bare)


    def restart_task(self, jid_bare):
        if jid_bare == self.boundjid.bare:
            return
        if jid_bare not in self.task_manager:
            self.task_manager[jid_bare] = {}
            logger.info('Creating new task manager for JID {}'.format(jid_bare))
        logger.info('Stopping task "interval" for JID {}'.format(jid_bare))
        try:
            self.task_manager[jid_bare]['interval'].cancel()
        except:
            logger.info('No task "interval" for JID {} (XmppChatTask.task_message)'
                        .format(jid_bare))
        logger.info('Starting tasks "interval" for JID {}'.format(jid_bare))
        self.task_manager[jid_bare]['interval'] = asyncio.create_task(
            XmppChatTask.task_message(self, jid_bare))