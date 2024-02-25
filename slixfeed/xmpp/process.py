#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

TODO

1) Deprecate "add" (see above) and make it interactive.
   Slixfeed: Do you still want to add this URL to subscription list?
   See: case _ if message_lowercase.startswith("add"):

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
import logging
import os
import slixfeed.action as action
import slixfeed.config as config
from slixfeed.dt import current_time, timestamp
import slixfeed.fetch as fetch
import slixfeed.sqlite as sqlite
import slixfeed.task as task
import slixfeed.url as uri
from slixfeed.version import __version__
from slixfeed.xmpp.bookmark import XmppBookmark
from slixfeed.xmpp.muc import XmppGroupchat
from slixfeed.xmpp.message import XmppMessage
from slixfeed.xmpp.presence import XmppPresence
from slixfeed.xmpp.upload import XmppUpload
from slixfeed.xmpp.utility import get_chat_type, is_moderator
import time


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
    if message['type'] in ('chat', 'groupchat', 'normal'):
        jid = message['from'].bare
        jid_file = jid
        message_text = ' '.join(message['body'].split())
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
            if not is_moderator(self, jid, jid_full):
                return

        # NOTE This is an exceptional case in which we treat
        # type groupchat the same as type chat in a way that
        # doesn't require an exclamation mark for actionable
        # command.
        if (message_text.lower().startswith('http') and
            message_text.lower().endswith('.opml')):
            url = message_text
            task.clean_tasks_xmpp(self, jid, ['status'])
            status_type = 'dnd'
            status_message = '📥️ Procesing request to import feeds...'
            XmppPresence.send(self, jid, status_message,
                              status_type=status_type)
            db_file = config.get_pathname_to_database(jid_file)
            count = await action.import_opml(db_file, url)
            if count:
                response = 'Successfully imported {} feeds.'.format(count)
            else:
                response = 'OPML file was not imported.'
            await task.start_tasks_xmpp(self, jid, ['status'])
            XmppMessage.send_reply(self, message, response)
            return


        if message['type'] == 'groupchat':
            # nick = message['from'][message['from'].index('/')+1:]
            # nick = str(message['from'])
            # nick = nick[nick.index('/')+1:]
            if (message['muc']['nick'] == self.alias or
                not message['body'].startswith('!')):
                return
            # token = await initdb(
            #     jid,
            #     sqlite.get_setting_value,
            #     'token'
            #     )
            # if token == 'accepted':
            #     operator = await initdb(
            #         jid,
            #         sqlite.get_setting_value,
            #         'masters'
            #         )
            #     if operator:
            #         if nick not in operator:
            #             return
            # approved = False
            jid_full = str(message['from'])
            if not is_moderator(self, jid, jid_full):
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
            #         jid,
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

        # await compose.message(self, jid, message)

        if message['type'] == 'groupchat':
            message_text = message_text[1:]
        message_lowercase = message_text.lower()

        logging.debug([str(message['from']), ':', message_text])

        # Support private message via groupchat
        # See https://codeberg.org/poezio/slixmpp/issues/3506
        if message['type'] == 'chat' and message.get_plugin('muc', check=True):
            jid_bare = message['from'].bare
            jid_full = str(message['from'])
            if (jid_bare == jid_full[:jid_full.index('/')]):
                jid = str(message['from'])
                jid_file = jid_full.replace('/', '_')

        response = None
        match message_lowercase:
            # case 'breakpoint':
            #     if jid == get_value('accounts', 'XMPP', 'operator'):
            #         breakpoint()
            #         print('task_manager[jid]')
            #         print(task_manager[jid])
            #         await self.get_roster()
            #         print('roster 1')
            #         print(self.client_roster)
            #         print('roster 2')
            #         print(self.client_roster.keys())
            #         print('jid')
            #         print(jid)
            #     else:
            #         response = (
            #             'This action is restricted. '
            #             'Type: breakpoint.'
            #             )
            #         XmppMessage.send_reply(self, message, response)
            case 'help':
                command_list = ' '.join(action.manual('commands.toml'))
                response = ('Available command keys:\n'
                            '```\n{}\n```\n'
                            'Usage: `help <key>`'
                            .format(command_list))
                print(response)
                XmppMessage.send_reply(self, message, response)
            case 'help all':
                command_list = action.manual('commands.toml', section='all')
                response = ('Complete list of commands:\n'
                            '```\n{}\n```'
                            .format(command_list))
                print(response)
                XmppMessage.send_reply(self, message, response)
            case _ if message_lowercase.startswith('help'):
                command = message_text[5:].lower()
                command = command.split(' ')
                if len(command) == 2:
                    command_root = command[0]
                    command_name = command[1]
                    command_list = action.manual('commands.toml',
                                                 section=command_root,
                                                 command=command_name)
                    if command_list:
                        command_list = ''.join(command_list)
                        response = (command_list)
                    else:
                        response = ('KeyError for {} {}'
                                    .format(command_root, command_name))
                elif len(command) == 1:
                    command = command[0]
                    command_list = action.manual('commands.toml', command)
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
                XmppMessage.send_reply(self, message, response)
            case 'info':
                command_list = action.manual('information.toml')
                response = ('Available command options:\n'
                            '```\n{}\n```\n'
                            'Usage: `info <option>`'
                            .format(command_list))
                XmppMessage.send_reply(self, message, response)
            case _ if message_lowercase.startswith('info'):
                command = message_text[5:].lower()
                command_list = action.manual('information.toml', command)
                if command_list:
                    # command_list = '\n'.join(command_list)
                    response = (command_list)
                else:
                    response = ('KeyError for {}'
                                .format(command))
                XmppMessage.send_reply(self, message, response)
            case _ if message_lowercase in ['greetings', 'hallo', 'hello',
                                            'hey', 'hi', 'hola', 'holla',
                                            'hollo']:
                response = ('Greeting! My name is {}.\n'
                            'I am an RSS News Bot.\n'
                            'Send "help" for further instructions.\n'
                            .format(self.alias))
                XmppMessage.send_reply(self, message, response)
    
            # case _ if message_lowercase.startswith('activate'):
            #     if message['type'] == 'groupchat':
            #         acode = message[9:]
            #         token = await initdb(
            #             jid,
            #             sqlite.get_setting_value,
            #             'token'
            #             )
            #         if int(acode) == token:
            #             await initdb(
            #                 jid,
            #                 sqlite.update_setting_value,
            #                 ['masters', nick]
            #                 )
            #             await initdb(
            #                 jid,
            #                 sqlite.update_setting_value,
            #                 ['token', 'accepted']
            #                 )
            #             response = '{}, your are in command.'.format(nick)
            #         else:
            #             response = 'Activation code is not valid.'
            #     else:
            #         response = 'This command is valid for groupchat only.'
            case _ if message_lowercase.startswith('add'):
                # Add given feed without validity check.
                message_text = message_text[4:]
                url = message_text.split(' ')[0]
                title = ' '.join(message_text.split(' ')[1:])
                if not title:
                    title = uri.get_hostname(url)
                if url.startswith('http'):
                    db_file = config.get_pathname_to_database(jid_file)
                    exist = await sqlite.get_feed_id_and_name(db_file, url)
                    if not exist:
                        await sqlite.insert_feed(db_file, url, title)
                        await action.scan(db_file, url)
                        old = config.get_setting_value(db_file, "old")
                        if old:
                            # task.clean_tasks_xmpp(self, jid, ['status'])
                            # await send_status(jid)
                            await task.start_tasks_xmpp(self, jid, ['status'])
                        else:
                            feed_id = await sqlite.get_feed_id(db_file, url)
                            feed_id = feed_id[0]
                            await sqlite.mark_feed_as_read(db_file, feed_id)
                        response = ('> {}\n'
                                    'News source has been '
                                    'added to subscription list.'
                                    .format(url))
                    else:
                        ix = exist[0]
                        name = exist[1]
                        response = ('> {}\n'
                                    'News source "{}" is already '
                                    'listed in the subscription list at '
                                    'index {}'
                                    .format(url, name, ix))
                else:
                    response = ('No action has been taken.'
                                '\n'
                                'Missing URL.')
                XmppMessage.send_reply(self, message, response)
            case _ if message_lowercase.startswith('allow +'):
                    key = message_text[:5]
                    val = message_text[7:]
                    if val:
                        db_file = config.get_pathname_to_database(jid_file)
                        keywords = sqlite.get_filter_value(db_file, key)
                        if keywords: keywords = str(keywords[0])
                        val = await config.add_to_list(val, keywords)
                        if sqlite.is_filter_key(db_file, key):
                            await sqlite.update_filter_value(db_file,
                                                              [key, val])
                        else:
                            await sqlite.set_filter_value(db_file, [key, val])
                        response = ('Approved keywords\n'
                                    '```\n{}\n```'
                                    .format(val))
                    else:
                        response = ('No action has been taken.'
                                    '\n'
                                    'Missing keywords.')
                    XmppMessage.send_reply(self, message, response)
            case _ if message_lowercase.startswith('allow -'):
                    key = message_text[:5]
                    val = message_text[7:]
                    if val:
                        db_file = config.get_pathname_to_database(jid_file)
                        keywords = sqlite.get_filter_value(db_file, key)
                        if keywords: keywords = str(keywords[0])
                        val = await config.remove_from_list(val, keywords)
                        if sqlite.is_filter_key(db_file, key):
                            await sqlite.update_filter_value(db_file,
                                                              [key, val])
                        else:
                            await sqlite.set_filter_value(db_file, [key, val])
                        response = ('Approved keywords\n'
                                    '```\n{}\n```'
                                    .format(val))
                    else:
                        response = ('No action has been taken.'
                                    '\n'
                                    'Missing keywords.')
                    XmppMessage.send_reply(self, message, response)
            case _ if message_lowercase.startswith('archive'):
                key = message_text[:7]
                val = message_text[8:]
                if val:
                    try:
                        if int(val) > 500:
                            response = 'Value may not be greater than 500.'
                        else:
                            db_file = config.get_pathname_to_database(jid_file)
                            await config.set_setting_value(db_file, key, val)
                            response = ('Maximum archived items has '
                                        'been set to {}.'
                                        .format(val))
                    except:
                        response = ('No action has been taken.'
                                    '\n'
                                    'Enter a numeric value only.')
                else:
                    response = ('No action has been taken.'
                                '\n'
                                'Missing value.')
                XmppMessage.send_reply(self, message, response)
            case _ if message_lowercase.startswith('bookmark +'):
                if jid == config.get_value('accounts', 'XMPP', 'operator'):
                    muc_jid = message_text[11:]
                    await XmppBookmark.add(self, jid=muc_jid)
                    response = ('Groupchat {} has been added to bookmarks.'
                                .format(muc_jid))
                else:
                    response = ('This action is restricted. '
                                'Type: adding bookmarks.')
                XmppMessage.send_reply(self, message, response)
            case _ if message_lowercase.startswith('bookmark -'):
                if jid == config.get_value('accounts', 'XMPP', 'operator'):
                    muc_jid = message_text[11:]
                    await XmppBookmark.remove(self, muc_jid)
                    response = ('Groupchat {} has been removed from bookmarks.'
                                .format(muc_jid))
                else:
                    response = ('This action is restricted. '
                                'Type: removing bookmarks.')
                XmppMessage.send_reply(self, message, response)
            case _ if message_lowercase.startswith('default '):
                key = message_text[8:]
                db_file = config.get_pathname_to_database(jid_file)
                await sqlite.delete_setting(db_file, key)
                response = ('Setting {} has been restored to default value.'
                            .format(key))
                XmppMessage.send_reply(self, message, response)
            case 'defaults':
                db_file = config.get_pathname_to_database(jid_file)
                await sqlite.delete_settings(db_file)
                response = 'Default settings have been restored.'
                XmppMessage.send_reply(self, message, response)
            case _ if message_lowercase.startswith('clear '):
                key = message_text[6:]
                db_file = config.get_pathname_to_database(jid_file)
                await sqlite.delete_filter(db_file, key)
                response = 'Filter {} has been purged.'.format(key)
                XmppMessage.send_reply(self, message, response)
            case 'bookmarks':
                if jid == config.get_value('accounts', 'XMPP', 'operator'):
                    response = await action.list_bookmarks(self)
                else:
                    response = ('This action is restricted. '
                                'Type: viewing bookmarks.')
                XmppMessage.send_reply(self, message, response)
            case _ if message_lowercase.startswith('deny +'):
                    key = message_text[:4]
                    val = message_text[6:]
                    if val:
                        db_file = config.get_pathname_to_database(jid_file)
                        keywords = sqlite.get_filter_value(db_file, key)
                        if keywords: keywords = str(keywords[0])
                        val = await config.add_to_list(val, keywords)
                        if sqlite.is_filter_key(db_file, key):
                            await sqlite.update_filter_value(db_file,
                                                              [key, val])
                        else:
                            await sqlite.set_filter_value(db_file, [key, val])
                        response = ('Rejected keywords\n'
                                    '```\n{}\n```'
                                    .format(val))
                    else:
                        response = ('No action has been taken.'
                                    '\n'
                                    'Missing keywords.')
                    XmppMessage.send_reply(self, message, response)
            case _ if message_lowercase.startswith('deny -'):
                    key = message_text[:4]
                    val = message_text[6:]
                    if val:
                        db_file = config.get_pathname_to_database(jid_file)
                        keywords = sqlite.get_filter_value(db_file, key)
                        if keywords: keywords = str(keywords[0])
                        val = await config.remove_from_list(val, keywords)
                        if sqlite.is_filter_key(db_file, key):
                            await sqlite.update_filter_value(db_file,
                                                              [key, val])
                        else:
                            await sqlite.set_filter_value(db_file, [key, val])
                        response = ('Rejected keywords\n'
                                    '```\n{}\n```'
                                    .format(val))
                    else:
                        response = ('No action has been taken.'
                                    '\n'
                                    'Missing keywords.')
                    XmppMessage.send_reply(self, message, response)
            case _ if message_lowercase.startswith('export'):
                ext = message_text[7:]
                if ext in ('md', 'opml'): # html xbel
                    status_type = 'dnd'
                    status_message = ('📤️ Procesing request to '
                                      'export feeds into {}...'
                                      .format(ext.upper()))
                    XmppPresence.send(self, jid, status_message,
                                      status_type=status_type)
                    filename = await action.export_feeds(self, jid, jid_file,
                                                         ext)
                    url = await XmppUpload.start(self, jid, filename)
                    # response = (
                    #     'Feeds exported successfully to {}.\n{}'
                    #     ).format(ex, url)
                    # XmppMessage.send_oob_reply_message(message, url, response)
                    chat_type = await get_chat_type(self, jid)
                    XmppMessage.send_oob(self, jid, url, chat_type)
                    await task.start_tasks_xmpp(self, jid, ['status'])
                else:
                    response = ('Unsupported filetype.\n'
                                'Try: md or opml')
                    XmppMessage.send_reply(self, message, response)
            case _ if (message_lowercase.startswith('gemini:') or
                       message_lowercase.startswith('gopher:')):
                response = 'Gemini and Gopher are not supported yet.'
                XmppMessage.send_reply(self, message, response)
            # TODO xHTML, HTMLZ, MHTML
            case _ if (message_lowercase.startswith('content') or
                       message_lowercase.startswith('page')):
                if message_lowercase.startswith('content'):
                    message_text = message_text[8:]
                    readability = True
                else:
                    message_text = message_text[5:]
                    readability = False
                ix_url = message_text.split(' ')[0]
                ext = ' '.join(message_text.split(' ')[1:])
                ext = ext if ext else 'pdf'
                url = None
                error = None
                response = None
                if ext in ('epub', 'html', 'markdown', 'md', 'pdf', 'text',
                           'txt'):
                    match ext:
                        case 'markdown':
                            ext = 'md'
                        case 'text':
                            ext = 'txt'
                    status_type = 'dnd'
                    status_message = ('📃️ Procesing request to produce {} '
                                      'document...'.format(ext.upper()))
                    XmppPresence.send(self, jid, status_message,
                                      status_type=status_type)
                    db_file = config.get_pathname_to_database(jid_file)
                    cache_dir = config.get_default_cache_directory()
                    if not os.path.isdir(cache_dir):
                        os.mkdir(cache_dir)
                    if not os.path.isdir(cache_dir + '/readability'):
                        os.mkdir(cache_dir + '/readability')
                    if ix_url:
                        try:
                            ix = int(ix_url)
                            try:
                                url = sqlite.get_entry_url(db_file, ix)
                                url = url[0]
                            except:
                                response = 'No entry with index {}'.format(ix)
                        except:
                            url = ix_url
                        if url:
                            url = uri.remove_tracking_parameters(url)
                            url = (uri.replace_hostname(url, 'link')) or url
                            result = await fetch.http(url)
                            if not result['error']:
                                data = result['content']
                                code = result['status_code']
                                title = get_document_title(data)
                                title = title.strip().lower()
                                for i in (' ', '-'):
                                    title = title.replace(i, '_')
                                for i in ('?', '"', '\'', '!'):
                                    title = title.replace(i, '')
                                filename = os.path.join(
                                    cache_dir, 'readability',
                                    title + '_' + dt.timestamp() + '.' + ext)
                                error = action.generate_document(data, url,
                                                                 ext, filename,
                                                                 readability)
                                if error:
                                    response = ('> {}\n'
                                                'Failed to export {}.  '
                                                'Reason: {}'.format(url,
                                                                    ext.upper(),
                                                                    error))
                                else:
                                    url = await XmppUpload.start(self, jid,
                                                                 filename)
                                    chat_type = await get_chat_type(self, jid)
                                    XmppMessage.send_oob(self, jid, url,
                                                         chat_type)
                            else:
                                response = ('> {}\n'
                                            'Failed to fetch URL.  Reason: {}'
                                            .format(url, code))
                        await task.start_tasks_xmpp(self, jid, ['status'])
                    else:
                        response = ('No action has been taken.'
                                    '\n'
                                    'Missing argument. '
                                    'Enter URL or entry index number.')
                else:
                    response = ('Unsupported filetype.\n'
                                'Try: epub, html, md (markdown), '
                                'pdf, or txt (text)')
                if response:
                    logging.warning('Error for URL {}: {}'.format(url, error))
                    XmppMessage.send_reply(self, message, response)
            case _ if (message_lowercase.startswith('http')) and(
                message_lowercase.endswith('.opml')):
                url = message_text
                task.clean_tasks_xmpp(self, jid, ['status'])
                status_type = 'dnd'
                status_message = '📥️ Procesing request to import feeds...'
                XmppPresence.send(self, jid, status_message,
                                  status_type=status_type)
                db_file = config.get_pathname_to_database(jid_file)
                count = await action.import_opml(db_file, url)
                if count:
                    response = ('Successfully imported {} feeds.'
                                .format(count))
                else:
                    response = 'OPML file was not imported.'
                await task.start_tasks_xmpp(self, jid, ['status'])
                XmppMessage.send_reply(self, message, response)
            case _ if (message_lowercase.startswith('http') or
                       message_lowercase.startswith('feed:')):
                url = message_text
                # task.clean_tasks_xmpp(self, jid, ['status'])
                status_type = 'dnd'
                status_message = ('📫️ Processing request to fetch data from {}'
                                  .format(url))
                XmppPresence.send(self, jid, status_message,
                                  status_type=status_type)
                if url.startswith('feed:'):
                    url = uri.feed_to_http(url)
                url = (uri.replace_hostname(url, 'feed')) or url
                db_file = config.get_pathname_to_database(jid_file)
                # try:
                result = await action.add_feed(db_file, url)
                if isinstance(result, list):
                    results = result
                    response = ("Web feeds found for {}\n\n```\n"
                                .format(url))
                    for result in results:
                        response += ("Title : {}\n"
                                     "Link  : {}\n"
                                     "\n"
                                     .format(result['name'], result['link']))
                    response += ('```\nTotal of {} feeds.'
                                .format(len(results)))
                elif result['exist']:
                    response = ('> {}\nNews source "{}" is already '
                                'listed in the subscription list at '
                                'index {}'.format(result['link'],
                                                  result['name'],
                                                  result['index']))
                elif result['error']:
                    response = ('> {}\nFailed to load URL.  Reason: {}'
                                .format(url, result['code']))
                else:
                    response = ('> {}\nNews source "{}" has been '
                                'added to subscription list.'
                                .format(result['link'], result['name']))
                # task.clean_tasks_xmpp(self, jid, ['status'])
                await task.start_tasks_xmpp(self, jid, ['status'])
                # except:
                #     response = (
                #         '> {}\nNews source is in the process '
                #         'of being added to the subscription '
                #         'list.'.format(url)
                #         )
                XmppMessage.send_reply(self, message, response)
            case _ if message_lowercase.startswith('feeds'):
                query = message_text[6:]
                if query:
                    if len(query) > 3:
                        db_file = config.get_pathname_to_database(jid_file)
                        response = action.list_feeds_by_query(db_file, query)
                    else:
                        response = 'Enter at least 4 characters to search'
                else:
                    db_file = config.get_pathname_to_database(jid_file)
                    result = await sqlite.get_feeds(db_file)
                    response = action.list_feeds(result)
                XmppMessage.send_reply(self, message, response)
            case 'goodbye':
                if message['type'] == 'groupchat':
                    XmppGroupchat.leave(self, jid)
                    await XmppBookmark.remove(self, jid)
                else:
                    response = 'This command is valid in groupchat only.'
                XmppMessage.send_reply(self, message, response)
            case _ if message_lowercase.startswith('interval'):
                key = message_text[:8]
                val = message_text[9:]
                if val:
                    try:
                        val = int(val)
                        db_file = config.get_pathname_to_database(jid_file)
                        await config.set_setting_value(db_file, key, val)
                        # NOTE Perhaps this should be replaced by functions
                        # clean and start
                        await task.refresh_task(self, jid, task.task_send, key,
                                                val)
                        response = ('Updates will be sent every {} minutes.'
                                    .format(val))
                    except:
                        response = ('No action has been taken.'
                                    '\n'
                                    'Enter a numeric value only.')
                else:
                    response = 'Missing value.'
                XmppMessage.send_reply(self, message, response)
            case _ if message_lowercase.startswith('join'):
                muc_jid = uri.check_xmpp_uri(message_text[5:])
                if muc_jid:
                    # TODO probe JID and confirm it's a groupchat
                    XmppGroupchat.join(self, jid, muc_jid)
                    # await XmppBookmark.add(self, jid=muc_jid)
                    response = ('Joined groupchat {}'
                                .format(message_text))
                else:
                    response = ('> {}\n'
                                'XMPP URI is not valid.'
                                .format(message_text))
                XmppMessage.send_reply(self, message, response)
            case _ if message_lowercase.startswith('length'):
                    key = message_text[:6]
                    val = message_text[7:]
                    if val:
                        try:
                            val = int(val)
                            db_file = config.get_pathname_to_database(jid_file)
                            await config.set_setting_value(db_file, key, val)
                            if val == 0: # if not val:
                                response = 'Summary length limit is disabled.'
                            else:
                                response = ('Summary maximum length '
                                            'is set to {} characters.'
                                            .format(val))
                        except:
                            response = ('No action has been taken.'
                                        '\n'
                                        'Enter a numeric value only.')
                    else:
                        response = ('No action has been taken.'
                                    '\n'
                                    'Missing value.')
            # case _ if message_lowercase.startswith('mastership'):
            #         key = message_text[:7]
            #         val = message_text[11:]
            #         if val:
            #             names = await initdb(
            #                 jid,
            #                 sqlite.get_setting_value,
            #                 key
            #                 )
            #             val = await config.add_to_list(
            #                 val,
            #                 names
            #                 )
            #             await initdb(
            #                 jid,
            #                 sqlite.update_setting_valuevv,
            #                 [key, val]
            #                 )
            #             response = (
            #                 'Operators\n'
            #                 '```\n{}\n```'
            #                 ).format(val)
            #         else:
            #             response = 'Missing value.'
                    XmppMessage.send_reply(self, message, response)
            case 'media off':
                db_file = config.get_pathname_to_database(jid_file)
                key = 'media'
                val = 0
                await config.set_setting_value(db_file, key, val)
                response = 'Media is disabled.'
                XmppMessage.send_reply(self, message, response)
            case 'media on':
                db_file = config.get_pathname_to_database(jid_file)
                key = 'media'
                val = 1
                await config.set_setting_value(db_file, key, val)
                response = 'Media is enabled.'
                XmppMessage.send_reply(self, message, response)
            case 'new':
                db_file = config.get_pathname_to_database(jid_file)
                key = 'old'
                val = 0
                await config.set_setting_value(db_file, key, val)
                response = 'Only new items of newly added feeds be delivered.'
                XmppMessage.send_reply(self, message, response)
            case _ if message_lowercase.startswith('next'):
                num = message_text[5:]
                if num:
                    await action.xmpp_send_update(self, jid, num)
                else:
                    await action.xmpp_send_update(self, jid)
                await task.start_tasks_xmpp(self, jid, ['status'])
            case 'old':
                db_file = config.get_pathname_to_database(jid_file)
                key = 'old'
                val = 1
                await config.set_setting_value(db_file, key, val)
                response = 'All items of newly added feeds be delivered.'
                XmppMessage.send_reply(self, message, response)
            case _ if message_lowercase.startswith('quantum'):
                key = message_text[:7]
                val = message_text[8:]
                if val:
                    try:
                        val = int(val)
                        # response = (
                        #     'Every update will contain {} news items.'
                        #     ).format(response)
                        db_file = config.get_pathname_to_database(jid_file)
                        await config.set_setting_value(db_file, key, val)
                        response = ('Next update will contain {} news items.'
                                    .format(val))
                    except:
                        response = ('No action has been taken.'
                                    '\n'
                                    'Enter a numeric value only.')
                else:
                    response = ('No action has been taken.'
                                '\n'
                                'Missing value.')
                XmppMessage.send_reply(self, message, response)
            case 'random':
                # TODO /questions/2279706/select-random-row-from-a-sqlite-table
                # NOTE sqlitehandler.get_entry_unread
                response = 'Updates will be sent by random order.'
                XmppMessage.send_reply(self, message, response)
            case _ if message_lowercase.startswith('read'):
                data = message_text[5:]
                data = data.split()
                url = data[0]
                if url:
                    task.clean_tasks_xmpp(self, jid, ['status'])
                    status_type = 'dnd'
                    status_message = ('📫️ Processing request to fetch data from {}'
                                      .format(url))
                    XmppPresence.send(self, jid, status_message,
                                      status_type=status_type)
                    if url.startswith('feed:'):
                        url = uri.feed_to_http(url)
                    url = (uri.replace_hostname(url, 'feed')) or url
                    match len(data):
                        case 1:
                            if url.startswith('http'):
                                response = await action.view_feed(url)
                            else:
                                response = ('No action has been taken.'
                                            '\n'
                                            'Missing URL.')
                        case 2:
                            num = data[1]
                            if url.startswith('http'):
                                response = await action.view_entry(url, num)
                            else:
                                response = ('No action has been taken.'
                                            '\n'
                                            'Missing URL.')
                        case _:
                            response = ('Enter command as follows:\n'
                                        '`read <url>` or `read <url> <number>`\n'
                                        'URL must not contain white space.')
                else:
                    response = ('No action has been taken.'
                                '\n'
                                'Missing URL.')
                XmppMessage.send_reply(self, message, response)
                await task.start_tasks_xmpp(self, jid, ['status'])
            case _ if message_lowercase.startswith('recent'):
                num = message_text[7:]
                if num:
                    try:
                        num = int(num)
                        if num < 1 or num > 50:
                            response = 'Value must be ranged from 1 to 50.'
                        else:
                            db_file = config.get_pathname_to_database(jid_file)
                            result = await sqlite.last_entries(db_file, num)
                            response = action.list_last_entries(result, num)
                    except:
                        response = ('No action has been taken.'
                                    '\n'
                                    'Enter a numeric value only.')
                else:
                    response = ('No action has been taken.'
                                '\n'
                                'Missing value.')
                XmppMessage.send_reply(self, message, response)
            case _ if message_lowercase.startswith('remove'):
                ix_url = message_text[7:]
                if ix_url:
                    db_file = config.get_pathname_to_database(jid_file)
                    try:
                        ix = int(ix_url)
                        url = sqlite.get_feed_url(db_file, ix)
                        if url:
                            url = url[0]
                            name = sqlite.get_feed_title(db_file, ix)
                            name = name[0]
                            await sqlite.remove_feed_by_index(db_file, ix)
                            response = ('> {}\n'
                                        'News source "{}" has been '
                                        'removed from subscription list.'
                                        .format(url, name))
                        else:
                            response = ('No news source with index {}.'
                                        .format(ix))
                    except:
                        url = ix_url
                        feed_id = await sqlite.get_feed_id(db_file, url)
                        if feed_id:
                            feed_id = feed_id[0]
                            await sqlite.remove_feed_by_url(db_file, url)
                            response = ('> {}\n'
                                        'News source has been removed '
                                        'from subscription list.'
                                        .format(url))
                        else:
                            response = ('> {}\n'
                                        # 'No action has been made.'
                                        'News source does not exist. '
                                        .format(url))
                    # await refresh_task(
                    #     self,
                    #     jid,
                    #     send_status,
                    #     'status',
                    #     20
                    #     )
                    # task.clean_tasks_xmpp(self, jid, ['status'])
                    await task.start_tasks_xmpp(self, jid, ['status'])
                else:
                    response = ('No action has been taken.'
                                '\n'
                                'Missing argument. '
                                'Enter feed URL or index number.')
                XmppMessage.send_reply(self, message, response)
            case _ if message_lowercase.startswith('reset'):
                # TODO Reset also by ID
                ix_url = message_text[6:]
                task.clean_tasks_xmpp(self, jid, ['status'])
                status_type = 'dnd'
                status_message = '📫️ Marking entries as read...'
                XmppPresence.send(self, jid, status_message,
                                  status_type=status_type)
                db_file = config.get_pathname_to_database(jid_file)
                if ix_url:
                    db_file = config.get_pathname_to_database(jid_file)
                    try:
                        ix = int(ix_url)
                        url = sqlite.get_feed_url(db_file, ix)
                        if url:
                            url = url[0]
                            name = sqlite.get_feed_title(db_file, ix)
                            name = name[0]
                            await sqlite.mark_feed_as_read(db_file, ix)
                            response = ('> {}\n'
                                        'All entries of source "{}" have been '
                                        'marked as read.'
                                        .format(url, name))
                        else:
                            response = ('No news source with index {}.'
                                        .format(ix))
                    except:
                        url = ix_url
                        feed_id = await sqlite.get_feed_id(db_file, url)
                        if feed_id:
                            feed_id = feed_id[0]
                            name = sqlite.get_feed_title(db_file, feed_id)
                            name = name[0]
                            await sqlite.mark_feed_as_read(db_file, feed_id)
                            response = ('> {}\n'
                                        'All entries of source "{}" have been '
                                        'marked as read.'
                                        .format(url, name))
                        else:
                            response = ('> {}\n'
                                        # 'No action has been made.'
                                        'News source does not exist. '
                                        .format(url))
                else:
                    await sqlite.mark_all_as_read(db_file)
                    response = 'All entries have been marked as read.'
                XmppMessage.send_reply(self, message, response)
                await task.start_tasks_xmpp(self, jid, ['status'])
            case _ if message_lowercase.startswith('search'):
                query = message_text[7:]
                if query:
                    if len(query) > 1:
                        db_file = config.get_pathname_to_database(jid_file)
                        results = await sqlite.search_entries(db_file, query)
                        response = action.list_search_results(query, results)
                    else:
                        response = 'Enter at least 2 characters to search'
                else:
                    response = ('No action has been taken.'
                                '\n'
                                'Missing search query.')
                XmppMessage.send_reply(self, message, response)
            case 'start':
                key = 'enabled'
                val = 1
                db_file = config.get_pathname_to_database(jid_file)
                await config.set_setting_value(db_file, key, val)
                status_type = 'available'
                status_message = '📫️ Welcome back!'
                XmppPresence.send(self, jid, status_message, status_type=status_type)
                await asyncio.sleep(5)
                await task.start_tasks_xmpp(self, jid, ['check', 'status', 'interval'])
                response = 'Updates are enabled.'
                XmppMessage.send_reply(self, message, response)
            case 'stats':
                db_file = config.get_pathname_to_database(jid_file)
                response = await action.list_statistics(db_file)
                XmppMessage.send_reply(self, message, response)
            case _ if message_lowercase.startswith('disable '):
                feed_id = message_text[8:]
                db_file = config.get_pathname_to_database(jid_file)
                try:
                    await sqlite.set_enabled_status(db_file, feed_id, 0)
                    await sqlite.mark_feed_as_read(db_file, feed_id)
                    name = sqlite.get_feed_title(db_file, feed_id)[0]
                    addr = sqlite.get_feed_url(db_file, feed_id)[0]
                    response = ('> {}\n'
                                'Updates are now disabled for news source "{}"'
                                .format(addr, name))
                except:
                    response = ('No action has been taken.'
                                '\n'
                                'No news source with index {}.'
                                .format(feed_id))
                XmppMessage.send_reply(self, message, response)
                await task.start_tasks_xmpp(self, jid, ['status'])
            case _ if message_lowercase.startswith('rename'):
                message_text = message_text[7:]
                feed_id = message_text.split(' ')[0]
                name = ' '.join(message_text.split(' ')[1:])
                if name:
                    try:
                        feed_id = int(feed_id)
                        db_file = config.get_pathname_to_database(jid_file)
                        name_old = sqlite.get_feed_title(db_file, feed_id)
                        if name_old:
                            name_old = name_old[0]
                            if name == name_old:
                                response = ('No action has been taken.'
                                            '\n'
                                            'Input name is identical to the '
                                            'existing name.')
                            else:
                                await sqlite.set_feed_title(db_file, feed_id, name)
                                response = ('> {}'
                                            '\n'
                                            'Subscription #{} has been renamed to "{}".'
                                            .format(name_old, feed_id, name))
                        else:
                            response = ('Subscription with Id {} does not exist.'
                                        .format(feed_id))
                    except:
                        response = ('No action has been taken.'
                                    '\n'
                                    'Subscription Id must be a numeric value.')
                else:
                    response = ('No action has been taken.'
                                '\n'
                                'Missing argument. '
                                'Enter subscription Id and name.')
                XmppMessage.send_reply(self, message, response)
            case _ if message_lowercase.startswith('enable'):
                feed_id = message_text[7:]
                db_file = config.get_pathname_to_database(jid_file)
                try:
                    await sqlite.set_enabled_status(db_file, feed_id, 1)
                    name = sqlite.get_feed_title(db_file, feed_id)[0]
                    addr = sqlite.get_feed_url(db_file, feed_id)[0]
                    response = ('> {}\n'
                                'Updates are now enabled for news source "{}"'
                                .format(addr, name))
                except:
                    response = ('No action has been taken.'
                                '\n'
                                'No news source with index {}.'.format(ix))
                XmppMessage.send_reply(self, message, response)
            case 'stop':
                key = 'enabled'
                val = 0
                db_file = config.get_pathname_to_database(jid_file)
                await config.set_setting_value(db_file, key, val)
                task.clean_tasks_xmpp(self, jid, ['interval', 'status'])
                status_type = 'xa'
                status_message = '📪️ Send "Start" to receive Jabber updates'
                XmppPresence.send(self, jid, status_message,
                                  status_type=status_type)
                response = 'Updates are disabled.'
                XmppMessage.send_reply(self, message, response)
            case 'support':
                muc_jid = 'slixfeed@chat.woodpeckersnest.space'
                response = 'Join xmpp:{}?join'.format(muc_jid)
                XmppMessage.send_reply(self, message, response)
                if await get_chat_type(self, jid) == 'chat':
                    self.plugin['xep_0045'].invite(muc_jid, jid)
            case 'version':
                response = __version__
                XmppMessage.send_reply(self, message, response)
            case _ if message_lowercase.startswith('xmpp:'):
                muc_jid = uri.check_xmpp_uri(message_text)
                if muc_jid:
                    # TODO probe JID and confirm it's a groupchat
                    XmppGroupchat.join(self, jid, muc_jid)
                    # await XmppBookmark.add(self, jid=muc_jid)
                    response = ('Joined groupchat {}'
                                .format(message_text))
                else:
                    response = ('> {}\n'
                                'XMPP URI is not valid.'
                                .format(message_text))
                XmppMessage.send_reply(self, message, response)
            case _:
                response = ('Unknown command. '
                            'Press "help" for list of commands')
                XmppMessage.send_reply(self, message, response)
        # TODO Use message correction here
        # NOTE This might not be a good idea if
        # commands are sent one close to the next
        # if response: message.reply(response).send()

        command_time_finish = time.time()
        command_time_total = command_time_finish - command_time_start
        command_time_total = round(command_time_total, 3)
        response = 'Finished. Total time: {}s'.format(command_time_total)
        XmppMessage.send_reply(self, message, response)

        if not response: response = 'EMPTY MESSAGE - ACTION ONLY'
        data_dir = config.get_default_data_directory()
        if not os.path.isdir(data_dir):
            os.mkdir(data_dir)
        if not os.path.isdir(data_dir + '/logs/'):
            os.mkdir(data_dir + '/logs/')
        action.log_to_markdown(
            current_time(), os.path.join(data_dir, 'logs', jid_file),
            jid, message_text)
        action.log_to_markdown(
            current_time(), os.path.join(data_dir, 'logs', jid_file),
            self.boundjid.bare, response)

        print(
            'Message : {}\n'
            'JID     : {}\n'
            'File    : {}\n'
            '{}\n'
            .format(message_text, jid, jid_file, response)
            )
