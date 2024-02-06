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

import logging
import os
import slixfeed.action as action
import slixfeed.config as config
from slixfeed.dt import current_time, timestamp
import slixfeed.fetch as fetch
import slixfeed.sqlite as sqlite
import slixfeed.task as task
import slixfeed.url as uri
from slixfeed.xmpp.bookmark import XmppBookmark
import slixfeed.xmpp.muc as groupchat
from slixfeed.xmpp.status import XmppStatus
import slixfeed.xmpp.upload as upload
from slixfeed.xmpp.utility import get_chat_type
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
            role = self.plugin['xep_0045'].get_jid_property(
                jid, jid_full[jid_full.index('/')+1:], 'role')
            if role != 'moderator':
                return

        # NOTE This is an exceptional case in which we treat
        # type groupchat the same as type chat in a way that
        # doesn't require an exclamation mark for actionable
        # command.
        if (message_text.lower().startswith('http') and
            message_text.lower().endswith('.opml')):
            url = message_text
            await task.clean_tasks_xmpp(jid, ['status'])
            status_type = 'dnd'
            status_message = '📥️ Procesing request to import feeds...'
            await XmppStatus.send(self, jid, status_message, status_type)
            db_file = config.get_pathname_to_database(jid_file)
            count = await action.import_opml(db_file, url)
            if count:
                response = 'Successfully imported {} feeds.'.format(count)
            else:
                response = 'OPML file was not imported.'
            # await task.clean_tasks_xmpp(jid, ['status'])
            await task.start_tasks_xmpp(self, jid, ['status'])
            send_reply_message(self, message, response)
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
            #     get_settings_value,
            #     'token'
            #     )
            # if token == 'accepted':
            #     operator = await initdb(
            #         jid,
            #         get_settings_value,
            #         'masters'
            #         )
            #     if operator:
            #         if nick not in operator:
            #             return
            # approved = False
            jid_full = str(message['from'])
            role = self.plugin['xep_0045'].get_jid_property(
                jid, jid_full[jid_full.index('/')+1:], 'role')
            if role != 'moderator':
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
            #         get_settings_value,
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
            #         send_reply_message(self, message, response)
            case 'help':
                command_list = ' '.join(action.manual('commands.toml'))
                response = ('Available command keys:\n'
                            '```\n{}\n```\n'
                            'Usage: `help <key>`'
                            .format(command_list))
                print(response)
                send_reply_message(self, message, response)
            case _ if message_lowercase.startswith('help'):
                command = message_text[5:]
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
                send_reply_message(self, message, response)
            case 'info':
                command_list = ' '.join(action.manual('information.toml'))
                response = ('Available command options:\n'
                            '```\n{}\n```\n'
                            'Usage: `info <option>`'
                            .format(command_list))
                send_reply_message(self, message, response)
            case _ if message_lowercase.startswith('info'):
                command = message_text[5:]
                command_list = action.manual('information.toml', command)
                if command_list:
                    # command_list = '\n'.join(command_list)
                    response = (command_list)
                else:
                    response = ('KeyError for {}'
                                .format(command))
                send_reply_message(self, message, response)
            case _ if message_lowercase in ['greetings', 'hallo', 'hello',
                                            'hey', 'hi', 'hola', 'holla',
                                            'hollo']:
                response = ('Greeting! My name is {}.\n'
                            'I am an RSS News Bot.\n'
                            'Send "help" for further instructions.\n'
                            .format(self.alias))
                send_reply_message(self, message, response)
    
            # case _ if message_lowercase.startswith('activate'):
            #     if message['type'] == 'groupchat':
            #         acode = message[9:]
            #         token = await initdb(
            #             jid,
            #             get_settings_value,
            #             'token'
            #             )
            #         if int(acode) == token:
            #             await initdb(
            #                 jid,
            #                 update_settings_value,
            #                 ['masters', nick]
            #                 )
            #             await initdb(
            #                 jid,
            #                 update_settings_value,
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
                        old = await config.get_setting_value(db_file, "old")
                        if old:
                            # await task.clean_tasks_xmpp(jid, ['status'])
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
                    response = 'Missing URL.'
                send_reply_message(self, message, response)
            case _ if message_lowercase.startswith('allow +'):
                    key = 'filter-' + message_text[:5]
                    val = message_text[7:]
                    if val:
                        db_file = config.get_pathname_to_database(jid_file)
                        keywords = await sqlite.get_filters_value(db_file, key)
                        val = await config.add_to_list(val, keywords)
                        if await sqlite.get_filters_value(db_file, key):
                            await sqlite.update_filters_value(db_file,
                                                              [key, val])
                        else:
                            await sqlite.set_filters_value(db_file, [key, val])
                        response = ('Approved keywords\n'
                                    '```\n{}\n```'
                                    .format(val))
                    else:
                        response = 'Missing keywords.'
                    send_reply_message(self, message, response)
            case _ if message_lowercase.startswith('allow -'):
                    key = 'filter-' + message_text[:5]
                    val = message_text[7:]
                    if val:
                        db_file = config.get_pathname_to_database(jid_file)
                        keywords = await sqlite.get_filters_value(db_file, key)
                        val = await config.remove_from_list(val, keywords)
                        if await sqlite.get_filters_value(db_file, key):
                            await sqlite.update_filters_value(db_file,
                                                              [key, val])
                        else:
                            await sqlite.set_filters_value(db_file, [key, val])
                        response = ('Approved keywords\n'
                                    '```\n{}\n```'
                                    .format(val))
                    else:
                        response = 'Missing keywords.'
                    send_reply_message(self, message, response)
            case _ if message_lowercase.startswith('archive'):
                key = message_text[:7]
                val = message_text[8:]
                if val:
                    try:
                        if int(val) > 500:
                            response = 'Value may not be greater than 500.'
                        else:
                            db_file = config.get_pathname_to_database(jid_file)
                            if await sqlite.get_settings_value(db_file,
                                                               [key, val]):
                                await sqlite.update_settings_value(db_file,
                                                                   [key, val])
                            else:
                                await sqlite.set_settings_value(db_file,
                                                                [key, val])
                            response = ('Maximum archived items has '
                                        'been set to {}.'
                                        .format(val))
                    except:
                        response = 'Enter a numeric value only.'
                else:
                    response = 'Missing value.'
                send_reply_message(self, message, response)
            case _ if message_lowercase.startswith('bookmark -'):
                if jid == config.get_value('accounts', 'XMPP', 'operator'):
                    muc_jid = message_text[11:]
                    await XmppBookmark.remove(self, muc_jid)
                    response = ('Groupchat {} has been removed '
                                'from bookmarks.'
                                .format(muc_jid))
                else:
                    response = ('This action is restricted. '
                                'Type: removing bookmarks.')
                send_reply_message(self, message, response)
            case 'bookmarks':
                if jid == config.get_value('accounts', 'XMPP', 'operator'):
                    response = await action.list_bookmarks(self)
                else:
                    response = ('This action is restricted. '
                                'Type: viewing bookmarks.')
                send_reply_message(self, message, response)
            case _ if message_lowercase.startswith('deny +'):
                    key = 'filter-' + message_text[:4]
                    val = message_text[6:]
                    if val:
                        db_file = config.get_pathname_to_database(jid_file)
                        keywords = await sqlite.get_filters_value(db_file, key)
                        val = await config.add_to_list(val, keywords)
                        if await sqlite.get_filters_value(db_file, key):
                            await sqlite.update_filters_value(db_file,
                                                              [key, val])
                        else:
                            await sqlite.set_filters_value(db_file, [key, val])
                        response = ('Rejected keywords\n'
                                    '```\n{}\n```'
                                    .format(val))
                    else:
                        response = 'Missing keywords.'
                    send_reply_message(self, message, response)
            case _ if message_lowercase.startswith('deny -'):
                    key = 'filter-' + message_text[:4]
                    val = message_text[6:]
                    if val:
                        db_file = config.get_pathname_to_database(jid_file)
                        keywords = await sqlite.get_filters_value(db_file, key)
                        val = await config.remove_from_list(val, keywords)
                        if await sqlite.get_filters_value(db_file, key):
                            await sqlite.update_filters_value(db_file,
                                                              [key, val])
                        else:
                            await sqlite.set_filters_value(db_file, [key, val])
                        response = ('Rejected keywords\n'
                                    '```\n{}\n```'
                                    .format(val))
                    else:
                        response = 'Missing keywords.'
                    send_reply_message(self, message, response)
            case _ if message_lowercase.startswith('export'):
                ex = message_text[7:]
                if ex in ('opml', 'html', 'md', 'xbel'):
                    status_type = 'dnd'
                    status_message = ('📤️ Procesing request to '
                                      'export feeds into {}...'
                                      .format(ex))
                    await XmppStatus.send(self, jid, status_message,
                                          status_type)
                    cache_dir = config.get_default_cache_directory()
                    if not os.path.isdir(cache_dir):
                        os.mkdir(cache_dir)
                    if not os.path.isdir(cache_dir + '/' + ex):
                        os.mkdir(cache_dir + '/' + ex)
                    filename = os.path.join(
                        cache_dir, ex, 'slixfeed_' + timestamp() + '.' + ex)
                    db_file = config.get_pathname_to_database(jid_file)
                    results = await sqlite.get_feeds(db_file)
                    match ex:
                        case 'html':
                            response = 'Not yet implemented.'
                        case 'md':
                            action.export_to_markdown(jid, filename, results)
                        case 'opml':
                            action.export_to_opml(jid, filename, results)
                        case 'xbel':
                            response = 'Not yet implemented.'
                    url = await upload.start(self, jid, filename)
                    # response = (
                    #     'Feeds exported successfully to {}.\n{}'
                    #     ).format(ex, url)
                    # send_oob_reply_message(message, url, response)
                    await send_oob_message(self, jid, url)
                    await task.start_tasks_xmpp(self, jid, ['status'])
                else:
                    response = ('Unsupported filetype.\n'
                                'Try: html, md, opml, or xbel')
                    send_reply_message(self, message, response)
            case _ if (message_lowercase.startswith('gemini:') or
                       message_lowercase.startswith('gopher:')):
                response = 'Gemini and Gopher are not supported yet.'
                send_reply_message(self, message, response)
            # TODO xHTML, HTMLZ, Markdown, MHTML, PDF, TXT
            case _ if (message_lowercase.startswith('get')):
                message_text = message_text[4:]
                ix_url = message_text.split(' ')[0]
                ext = ' '.join(message_text.split(' ')[1:])
                ext = ext if ext else 'pdf'
                url = None
                error = None
                if ext in ('epub', 'html', 'markdown',
                           'md', 'pdf', 'text', 'txt'):
                    match ext:
                        case 'markdown':
                            ext = 'md'
                        case 'text':
                            ext = 'txt'
                    status_type = 'dnd'
                    status_message = ('📃️ Procesing request to '
                                      'produce {} document...'
                                      .format(ext.upper()))
                    await XmppStatus.send(self, jid, status_message,
                                          status_type)
                    db_file = config.get_pathname_to_database(jid_file)
                    cache_dir = config.get_default_cache_directory()
                    if ix_url:
                        if not os.path.isdir(cache_dir):
                            os.mkdir(cache_dir)
                        if not os.path.isdir(cache_dir + '/readability'):
                            os.mkdir(cache_dir + '/readability')
                        try:
                            ix = int(ix_url)
                            try:
                                url = sqlite.get_entry_url(db_file, ix)
                            except:
                                response = 'No entry with index {}'.format(ix)
                        except:
                            url = ix_url
                        if url:
                            logging.info('Original URL: {}'
                                         .format(url))
                            url = uri.remove_tracking_parameters(url)
                            logging.info('Processed URL (tracker removal): {}'
                                         .format(url))
                            url = (uri.replace_hostname(url, 'link')) or url
                            logging.info('Processed URL (replace hostname): {}'
                                         .format(url))
                            result = await fetch.http(url)
                            data = result[0]
                            code = result[1]
                            if data:
                                title = action.get_document_title(data)
                                title = title.strip().lower()
                                for i in (' ', '-'):
                                    title = title.replace(i, '_')
                                for i in ('?', '"', '\'', '!'):
                                    title = title.replace(i, '')
                                filename = os.path.join(
                                    cache_dir, 'readability',
                                    title + '_' + timestamp() + '.' + ext)
                                error = action.generate_document(data, url,
                                                                 ext, filename)
                                if error:
                                    response = ('> {}\n'
                                                'Failed to export {}.  '
                                                'Reason: {}'
                                                .format(url, ext.upper(),
                                                        error))
                                else:
                                    url = await upload.start(self, jid,
                                                             filename)
                                    await send_oob_message(self, jid, url)
                            else:
                                response = ('> {}\n'
                                            'Failed to fetch URL.  Reason: {}'
                                            .format(url, code))
                        await task.start_tasks_xmpp(self, jid, ['status'])
                    else:
                        response = 'Missing entry index number.'
                else:
                    response = ('Unsupported filetype.\n'
                                'Try: epub, html, md (markdown), '
                                'pdf, or txt (text)')
                if response:
                    logging.warning('Error for URL {}: {}'.format(url, error))
                    send_reply_message(self, message, response)
            # case _ if (message_lowercase.startswith('http')) and(
            #     message_lowercase.endswith('.opml')):
            #     url = message_text
            #     await task.clean_tasks_xmpp(
            #         jid, ['status'])
            #     status_type = 'dnd'
            #     status_message = (
            #         '📥️ Procesing request to import feeds...'
            #         )
            #     await XmppStatus.send(
            #         self, jid, status_message, status_type)
            #     db_file = config.get_pathname_to_database(jid_file)
            #     count = await action.import_opml(db_file, url)
            #     if count:
            #         response = (
            #             'Successfully imported {} feeds.'
            #             ).format(count)
            #     else:
            #         response = (
            #             'OPML file was not imported.'
            #             )
            #     await task.clean_tasks_xmpp(
            #         jid, ['status'])
            #     await task.start_tasks_xmpp(
            #         self, jid, ['status'])
            #     send_reply_message(self, message, response)
            case _ if (message_lowercase.startswith('http') or
                       message_lowercase.startswith('feed:')):
                url = message_text
                # await task.clean_tasks_xmpp(jid, ['status'])
                status_type = 'dnd'
                status_message = ('📫️ Processing request '
                                  'to fetch data from {}'
                                  .format(url))
                await XmppStatus.send(self, jid, status_message, status_type)
                if url.startswith('feed:'):
                    url = uri.feed_to_http(url)
                url = (uri.replace_hostname(url, 'feed')) or url
                db_file = config.get_pathname_to_database(jid_file)
                # try:
                response = await action.add_feed(db_file, url)
                # await task.clean_tasks_xmpp(jid, ['status'])
                await task.start_tasks_xmpp(self, jid, ['status'])
                # except:
                #     response = (
                #         '> {}\nNews source is in the process '
                #         'of being added to the subscription '
                #         'list.'.format(url)
                #         )
                send_reply_message(self, message, response)
            case _ if message_lowercase.startswith('feeds'):
                query = message_text[6:]
                if query:
                    if len(query) > 3:
                        db_file = config.get_pathname_to_database(jid_file)
                        result = await sqlite.search_feeds(db_file, query)
                        response = action.list_feeds_by_query(query, result)
                    else:
                        response = 'Enter at least 4 characters to search'
                else:
                    db_file = config.get_pathname_to_database(jid_file)
                    result = await sqlite.get_feeds(db_file)
                    response = action.list_feeds(result)
                send_reply_message(self, message, response)
            case 'goodbye':
                if message['type'] == 'groupchat':
                    await groupchat.leave(self, jid)
                    await XmppBookmark.remove(self, muc_jid)
                else:
                    response = 'This command is valid in groupchat only.'
                send_reply_message(self, message, response)
            case _ if message_lowercase.startswith('interval'):
                key = message_text[:8]
                val = message_text[9:]
                await action.xmpp_change_interval(
                    self, key, val, jid, jid_file, message=message)
            case _ if message_lowercase.startswith('join'):
                muc_jid = uri.check_xmpp_uri(message_text[5:])
                if muc_jid:
                    # TODO probe JID and confirm it's a groupchat
                    await groupchat.join(self, jid, muc_jid)
                    response = ('Joined groupchat {}'
                                .format(message_text))
                else:
                    response = ('> {}\n'
                                'XMPP URI is not valid.'
                                .format(message_text))
                send_reply_message(self, message, response)
            case _ if message_lowercase.startswith('length'):
                    key = message_text[:6]
                    val = message_text[7:]
                    if val:
                        try:
                            val = int(val)
                            db_file = config.get_pathname_to_database(jid_file)
                            if await sqlite.get_settings_value(db_file,
                                                               [key, val]):
                                await sqlite.update_settings_value(db_file,
                                                                   [key, val])
                            else:
                                await sqlite.set_settings_value(db_file,
                                                                [key, val])
                            if val == 0: # if not val:
                                response = 'Summary length limit is disabled.'
                            else:
                                response = ('Summary maximum length '
                                            'is set to {} characters.'
                                            .format(val))
                        except:
                            response = 'Enter a numeric value only.'
                    else:
                        response = 'Missing value.'
            # case _ if message_lowercase.startswith('mastership'):
            #         key = message_text[:7]
            #         val = message_text[11:]
            #         if val:
            #             names = await initdb(
            #                 jid,
            #                 get_settings_value,
            #                 key
            #                 )
            #             val = await config.add_to_list(
            #                 val,
            #                 names
            #                 )
            #             await initdb(
            #                 jid,
            #                 update_settings_valuevv,
            #                 [key, val]
            #                 )
            #             response = (
            #                 'Operators\n'
            #                 '```\n{}\n```'
            #                 ).format(val)
            #         else:
            #             response = 'Missing value.'
                    send_reply_message(self, message, response)
            case 'new':
                db_file = config.get_pathname_to_database(jid_file)
                key = 'old'
                val = 0
                if await sqlite.get_settings_value(db_file, key):
                    await sqlite.update_settings_value(db_file, [key, val])
                else:
                    await sqlite.set_settings_value(db_file, [key, val])
                response = 'Only new items of newly added feeds will be sent.'
                send_reply_message(self, message, response)
            # TODO Will you add support for number of messages?
            case 'next':
                # num = message_text[5:]
                # await task.send_update(self, jid, num)

                await task.send_update(self, jid)

                # await task.clean_tasks_xmpp(
                #     jid, ['interval', 'status'])
                # await task.start_tasks_xmpp(
                #     self, jid, ['interval', 'status'])

                # await refresh_task(
                #     self,
                #     jid,
                #     send_update,
                #     'interval',
                #     num
                #     )
                # await refresh_task(
                #     self,
                #     jid,
                #     send_status,
                #     'status',
                #     20
                #     )
                # await refresh_task(jid, key, val)
            case 'old':
                db_file = config.get_pathname_to_database(jid_file)
                key = 'old'
                val = 1
                if await sqlite.get_settings_value(db_file, key):
                    await sqlite.update_settings_value(db_file, [key, val])
                else:
                    await sqlite.set_settings_value(db_file, [key, val])
                response = 'All items of newly added feeds will be sent.'
                send_reply_message(self, message, response)
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
                        if await sqlite.get_settings_value(db_file, key):
                            await sqlite.update_settings_value(db_file,
                                                               [key, val])
                        else:
                            await sqlite.set_settings_value(db_file,
                                                            [key, val])
                        response = ('Next update will contain {} news items.'
                                    .format(val))
                    except:
                        response = 'Enter a numeric value only.'
                else:
                    response = 'Missing value.'
                send_reply_message(self, message, response)
            case 'random':
                # TODO /questions/2279706/select-random-row-from-a-sqlite-table
                # NOTE sqlitehandler.get_entry_unread
                response = 'Updates will be sent by random order.'
                send_reply_message(self, message, response)
            case _ if message_lowercase.startswith('read'):
                data = message_text[5:]
                data = data.split()
                url = data[0]
                await task.clean_tasks_xmpp(jid, ['status'])
                status_type = 'dnd'
                status_message = ('📫️ Processing request to fetch data from {}'
                                  .format(url))
                await XmppStatus.send(self, jid, status_message, status_type)
                if url.startswith('feed:'):
                    url = uri.feed_to_http(url)
                url = (uri.replace_hostname(url, 'feed')) or url
                match len(data):
                    case 1:
                        if url.startswith('http'):
                            response = await action.view_feed(url)
                        else:
                            response = 'Missing URL.'
                    case 2:
                        num = data[1]
                        if url.startswith('http'):
                            response = await action.view_entry(url, num)
                        else:
                            response = 'Missing URL.'
                    case _:
                        response = ('Enter command as follows:\n'
                                    '`read <url>` or `read <url> <number>`\n'
                                    'URL must not contain white space.')
                send_reply_message(self, message, response)
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
                        response = 'Enter a numeric value only.'
                else:
                    response = 'Missing value.'
                send_reply_message(self, message, response)
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
                                        'News source does not exist. '
                                        'No action has been made.'
                                        .format(url))
                    # await refresh_task(
                    #     self,
                    #     jid,
                    #     send_status,
                    #     'status',
                    #     20
                    #     )
                    # await task.clean_tasks_xmpp(jid, ['status'])
                    await task.start_tasks_xmpp(self, jid, ['status'])
                else:
                    response = 'Missing feed URL or index number.'
                send_reply_message(self, message, response)
            case _ if message_lowercase.startswith('reset'):
                # TODO Reset also by ID
                ix_url = message_text[6:]
                await task.clean_tasks_xmpp(jid, ['status'])
                status_type = 'dnd'
                status_message = '📫️ Marking entries as read...'
                await XmppStatus.send(self, jid, status_message, status_type)
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
                                        'News source does not exist. '
                                        'No action has been made.'
                                        .format(url))
                else:
                    await sqlite.mark_all_as_read(db_file)
                    response = 'All entries have been marked as read.'
                send_reply_message(self, message, response)
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
                    response = 'Missing search query.'
                send_reply_message(self, message, response)
            case 'start':
                # response = 'Updates are enabled.'
                key = 'enabled'
                val = 1
                db_file = config.get_pathname_to_database(jid_file)
                if await sqlite.get_settings_value(db_file, key):
                    await sqlite.update_settings_value(db_file, [key, val])
                else:
                    await sqlite.set_settings_value(db_file, [key, val])
                await task.start_tasks_xmpp(self, jid)
                response = 'Updates are enabled.'
                # print(current_time(), 'task_manager[jid]')
                # print(task_manager[jid])
                send_reply_message(self, message, response)
            case 'stats':
                db_file = config.get_pathname_to_database(jid_file)
                response = await action.list_statistics(db_file)
                send_reply_message(self, message, response)
            case _ if message_lowercase.startswith('disable '):
                ix = message_text[8:]
                db_file = config.get_pathname_to_database(jid_file)
                try:
                    await sqlite.set_enabled_status(db_file, ix, 0)
                    response = ('Updates are now disabled for news source {}.'
                                .format(ix))
                except:
                    response = 'No news source with index {}.'.format(ix)
                send_reply_message(self, message, response)
            case _ if message_lowercase.startswith('enable'):
                ix = message_text[7:]
                db_file = config.get_pathname_to_database(jid_file)
                try:
                    await sqlite.set_enabled_status(db_file, ix, 1)
                    response = ('Updates are now enabled for news source {}.'
                                .format(ix))
                except:
                    response = 'No news source with index {}.'.format(ix)
                send_reply_message(self, message, response)
            case 'stop':
                await action.xmpp_stop_updates(self, message, jid, jid_file)
            case 'support':
                # TODO Send an invitation.
                response = 'Join xmpp:slixfeed@chat.woodpeckersnest.space?join'
                send_reply_message(self, message, response)
            case _ if message_lowercase.startswith('xmpp:'):
                muc_jid = uri.check_xmpp_uri(message_text)
                if muc_jid:
                    # TODO probe JID and confirm it's a groupchat
                    await groupchat.join(self, jid, muc_jid)
                    response = ('Joined groupchat {}'
                                .format(message_text))
                else:
                    response = ('> {}\n'
                                'XMPP URI is not valid.'
                                .format(message_text))
                send_reply_message(self, message, response)
            case _:
                response = ('Unknown command. '
                            'Press "help" for list of commands')
                send_reply_message(self, message, response)
        # TODO Use message correction here
        # NOTE This might not be a good idea if
        # commands are sent one close to the next
        # if response: message.reply(response).send()

        command_time_finish = time.time()
        command_time_total = command_time_finish - command_time_start
        command_time_total = round(command_time_total, 3)
        response = 'Finished. Total time: {}s'.format(command_time_total)
        send_reply_message(self, message, response)

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


def send_reply_message(self, message, response):
    message.reply(response).send()


# TODO Solve this function
def send_oob_reply_message(message, url, response):
    reply = message.reply(response)
    reply['oob']['url'] = url
    reply.send()


async def send_oob_message(self, jid, url):
    chat_type = await get_chat_type(self, jid)
    html = (
        f'<body xmlns="http://www.w3.org/1999/xhtml">'
        f'<a href="{url}">{url}</a></body>')
    message = self.make_message(
        mto=jid,
        mfrom=self.boundjid.bare,
        mbody=url,
        mhtml=html,
        mtype=chat_type
        )
    message['oob']['url'] = url
    message.send()


# def greet(self, jid, chat_type='chat'):
#     messages = [
#         'Greetings!',
#         'I'm {}, the news anchor.'.format(self.nick),
#         'My job is to bring you the latest news '
#         'from sources you provide me with.',
#         'You may always reach me via '
#         'xmpp:{}?message'.format(self.boundjid.bare)
#         ]
#     for message in messages:
#         self.send_message(
#             mto=jid,
#             mfrom=self.boundjid.bare,
#             mbody=message,
#             mtype=chat_type
#             )


def greet(self, jid, chat_type='chat'):
    message = (
        'Greetings!\n'
        'I am {}, the news anchor.\n'
        'My job is to bring you the latest '
        'news from sources you provide me with.\n'
        'You may always reach me via xmpp:{}?message').format(
            self.alias,
            self.boundjid.bare
            )
    self.send_message(
        mto=jid,
        mfrom=self.boundjid.bare,
        mbody=message,
        mtype=chat_type
        )

