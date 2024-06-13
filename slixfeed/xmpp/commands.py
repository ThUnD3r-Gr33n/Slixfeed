#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from feedparser import parse
from random import randrange
import slixfeed.config as config
from slixfeed.config import Config
import slixfeed.crawl as crawl
import slixfeed.dt as dt
import slixfeed.fetch as fetch
from slixfeed.log import Logger
import slixfeed.sqlite as sqlite
from slixfeed.syndication import Feed, Opml
import slixfeed.url as uri
from slixfeed.utilities import Documentation, Utilities
from slixfeed.version import __version__
from slixfeed.xmpp.bookmark import XmppBookmark
from slixfeed.xmpp.muc import XmppMuc
from slixfeed.xmpp.publish import XmppPubsub, XmppPubsubAction
from slixfeed.xmpp.presence import XmppPresence
from slixfeed.xmpp.status import XmppStatusTask
from slixfeed.xmpp.utilities import XmppUtilities
import sys

try:
    import tomllib
except:
    import tomli as tomllib

logger = Logger(__name__)


    # for task in main_task:
    #     task.cancel()

    # Deprecated in favour of event "presence_available"
    # if not main_task:
    #     await select_file()

class XmppCommands:


    def print_help():
        result = Documentation.manual('commands.toml')
        message = '\n'.join(result)
        return message


    def print_help_list():
        command_list = Documentation.manual('commands.toml', section='all')
        message = ('Complete list of commands:\n'
                   '```\n{}\n```'.format(command_list))
        return message


    def print_help_specific(command_root, command_name):
        command_list = Documentation.manual('commands.toml',
                                     section=command_root,
                                     command=command_name)
        if command_list:
            command_list = ''.join(command_list)
            message = (command_list)
        else:
            message = 'KeyError for {} {}'.format(command_root, command_name)
        return message


    def print_help_key(command):
        command_list = Documentation.manual('commands.toml', command)
        if command_list:
            command_list = ' '.join(command_list)
            message = ('Available command `{}` keys:\n'
                       '```\n{}\n```\n'
                       'Usage: `help {} <command>`'
                       .format(command, command_list, command))
        else:
            message = 'KeyError for {}'.format(command)
        return message


    def print_info_list():
        config_dir = config.get_default_config_directory()
        with open(config_dir + '/' + 'information.toml', mode="rb") as information:
            result = tomllib.load(information)
        message = '\n'.join(result)
        return message


    def print_info_specific(entry):
        config_dir = config.get_default_config_directory()
        with open(config_dir + '/' + 'information.toml', mode="rb") as information:
            entries = tomllib.load(information)
        if entry in entries:
            # command_list = '\n'.join(command_list)
            message = (entries[entry]['info'])
        else:
            message = 'KeyError for {}'.format(entry)
        return message


    async def feed_add(url, db_file, jid_bare, title=None):
        """
        Add given feed without validity check.

        Parameters
        ----------
        url : TYPE
            DESCRIPTION.
        db_file : TYPE
            DESCRIPTION.
        jid_bare : TYPE
            DESCRIPTION.
        title : TYPE, optional
            DESCRIPTION. The default is None.

        Returns
        -------
        response : TYPE
            DESCRIPTION.

        """
        if url.startswith('http'):
            if not title:
                title = uri.get_hostname(url)
            counter = 0
            hostname = uri.get_hostname(url)
            hostname = hostname.replace('.','-')
            identifier = hostname + ':' + str(counter)
            while True:
                if sqlite.check_identifier_exist(db_file, identifier):
                    counter += 1
                    identifier = hostname + ':' + str(counter)
                else:
                    break
            exist = sqlite.get_feed_id_and_name(db_file, url)
            if not exist:
                await sqlite.insert_feed(db_file, url, title,
                                         identifier)
                feed_id = sqlite.get_feed_id(db_file, url)
                feed_id = feed_id[0]
                result = await fetch.http(url)
                if not result['error']:
                    document = result['content']
                    feed = parse(document)
                    feed_valid = 0 if feed.bozo else 1
                    await sqlite.update_feed_validity(
                        db_file, feed_id, feed_valid)
                    if feed.has_key('updated_parsed'):
                        feed_updated = feed.updated_parsed
                        try:
                            feed_updated = dt.convert_struct_time_to_iso8601(
                                feed_updated)
                        except:
                            feed_updated = None
                    else:
                        feed_updated = None
                    feed_properties = Feed.get_properties_of_feed(
                        db_file, feed_id, feed)
                    await sqlite.update_feed_properties(db_file, feed_id,
                                                        feed_properties)
                    feed_id = sqlite.get_feed_id(db_file, url)
                    feed_id = feed_id[0]
                    new_entries = Feed.get_properties_of_entries(
                        jid_bare, db_file, url, feed_id, feed)
                    if new_entries:
                        await sqlite.add_entries_and_update_feed_state(
                            db_file, feed_id, new_entries)
    
                    # Function "scan" of module "actions" no longer exists.
                    # If you choose to add this download functionality and
                    # the look into function "check_updates" of module "task".
                    # await action.scan(self, jid_bare, db_file, url)
                    # if jid_bare not in self.settings:
                    #     Config.add_settings_jid(self.settings, jid_bare,
                    #                             db_file)
                    # old = Config.get_setting_value(self.settings, jid_bare,
                    #                                'old')
                    # if old:
                    #     # task.clean_tasks_xmpp_chat(self, jid_bare, ['status'])
                    #     # await send_status(jid)
                    #     Task.start(self, jid_bare, 'status')
                    # else:
                    #     feed_id = sqlite.get_feed_id(db_file, url)
                    #     feed_id = feed_id[0]
                    #     await sqlite.mark_feed_as_read(db_file, feed_id)
    
                message = ('> {}\n'
                           'News source has been '
                           'added to subscription list.'
                           .format(url))
            else:
                ix = exist[0]
                name = exist[1]
                message = ('> {}\n'
                           'News source "{}" is already '
                           'listed in the subscription list at '
                           'index {}'
                           .format(url, name, ix))
        else:
            message = ('No action has been taken.  Missing URL.')
        return message


    async def set_filter_allow(db_file, val, axis):
        """

        Parameters
        ----------
        db_file : str
            Database filename.
        val : str
            Keyword (word or phrase).
        axis : boolean
            True for + (plus) and False for - (minus).

        Returns
        -------
        None.

        """
        keywords = sqlite.get_filter_value(db_file, 'allow')
        if keywords: keywords = str(keywords[0])
        if axis:
            val = await config.add_to_list(val, keywords)
        else:
            val = await config.remove_from_list(val, keywords)
        if sqlite.is_filter_key(db_file, 'allow'):
            await sqlite.update_filter_value(db_file, ['allow', val])
        else:
            await sqlite.set_filter_value(db_file, ['allow', val])


    def get_archive(self, jid_bare):
        result = Config.get_setting_value(
            self.settings, jid_bare, 'archive')
        message = str(result)
        return message


    async def set_archive(self, db_file, jid_bare, val):
        try:
            val_new = int(val)
            if val_new > 500:
                message = 'Value may not be greater than 500.'
            else:
                val_old = Config.get_setting_value(
                    self.settings, jid_bare, 'archive')
                await Config.set_setting_value(
                    self.settings, jid_bare, db_file, 'archive', val_new)
                message = ('Maximum archived items has been set to {} (was: {}).'
                           .format(val_new, val_old))
        except:
            message = 'No action has been taken.  Enter a numeric value only.'
        return message


    async def bookmark_add(self, muc_jid):
        await XmppBookmark.add(self, jid=muc_jid)
        message = ('Groupchat {} has been added to bookmarks.'
                   .format(muc_jid))
        return message


    async def bookmark_del(self, muc_jid):
        await XmppBookmark.remove(self, muc_jid)
        message = ('Groupchat {} has been removed from bookmarks.'
                   .format(muc_jid))
        return message


    async def restore_default(self, jid_bare, key=None):
        if key:
            self.settings[jid_bare][key] = None
            db_file = config.get_pathname_to_database(jid_bare)
            await sqlite.delete_setting(db_file, key)
            message = ('Setting {} has been restored to default value.'
                        .format(key))
        else:
            del self.settings[jid_bare]
            db_file = config.get_pathname_to_database(jid_bare)
            await sqlite.delete_settings(db_file)
            message = 'Default settings have been restored.'
        return message


    async def clear_filter(db_file, key):
        await sqlite.delete_filter(db_file, key)
        message = 'Filter {} has been purged.'.format(key)
        return message


    async def print_bookmarks(self):
        conferences = await XmppBookmark.get_bookmarks(self)
        message = '\nList of groupchats:\n\n```\n'
        for conference in conferences:
            message += ('Name: {}\n'
                        'Room: {}\n'
                        '\n'
                        .format(conference['name'], conference['jid']))
        message += ('```\nTotal of {} groupchats.\n'.format(len(conferences)))
        return message


    async def set_filter_deny(db_file, val, axis):
        """

        Parameters
        ----------
        key : str
            deny.
        val : str
            keyword (word or phrase).
        axis : boolean
            True for + (plus) and False for - (minus).

        Returns
        -------
        None.

        """
        keywords = sqlite.get_filter_value(db_file, 'deny')
        if keywords: keywords = str(keywords[0])
        if axis:
            val = await config.add_to_list(val, keywords)
        else:
            val = await config.remove_from_list(val, keywords)
        if sqlite.is_filter_key(db_file, 'deny'):
            await sqlite.update_filter_value(db_file, ['deny', val])
        else:
            await sqlite.set_filter_value(db_file, ['deny', val])


    def export_feeds(jid_bare, ext):
        filename = Feed.export_feeds(jid_bare, ext)
        message = 'Feeds successfuly exported to {}.'.format(ext)
        return filename, message


    def fetch_gemini():
        message = 'Gemini and Gopher are not supported yet.'
        return message


    async def import_opml(self, db_file, jid_bare, command):
        url = command
        result = await fetch.http(url)
        count = await Opml.import_from_file(db_file, result)
        if count:
            message = ('Successfully imported {} feeds.'
                       .format(count))
        else:
            message = 'OPML file was not imported.'
        return message


    async def pubsub_list(self, jid):
        iq = await XmppPubsub.get_nodes(self, jid)
        message = ''
        for item in iq['disco_items']:
            item_id = item['node']
            item_name = item['name']
            message += 'Name: {}\nNode: {}\n\n'.format(item_name, item_id)
        return message


    # This is similar to send_next_update
    async def pubsub_send(self, info, jid_bare):
        # if num:
        #     report = await action.xmpp_pubsub_send_unread_items(
        #         self, jid, num)
        # else:
        #     report = await action.xmpp_pubsub_send_unread_items(
        #         self, jid)
        result = await XmppPubsubAction.send_unread_items(self, jid_bare)
        message = ''
        for url in result:
            if result[url]:
                message += url + ' : ' + str(result[url]) + '\n'


    # feed_add_custom_jid
    # TODO Consider removal due to the availability of IPC
    async def _pubsub_send(self, jid_bare, jid, info):
        # TODO Handle node error
        # sqlite3.IntegrityError: UNIQUE constraint failed: feeds_pubsub.node
        # ERROR:slixmpp.basexmpp:UNIQUE constraint failed: feeds_pubsub.node
        if len(info) > 1:
            jid = info[0]
            if '/' not in jid:
                url = info[1]
                db_file = config.get_pathname_to_database(jid)
                if len(info) > 2:
                    identifier = info[2]
                else:
                    counter = 0
                    hostname = uri.get_hostname(url)
                    hostname = hostname.replace('.','-')
                    identifier = hostname + ':' + str(counter)
                    while True:
                        if sqlite.check_identifier_exist(
                                db_file, identifier):
                            counter += 1
                            identifier = hostname + ':' + str(counter)
                        else:
                            break
                # task.clean_tasks_xmpp_chat(self, jid_bare, ['status'])
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
                if (url.startswith('feed:/') or
                    url.startswith('itpc:/') or
                    url.startswith('rss:/')):
                    url = uri.feed_to_http(url)
                url = (await uri.replace_hostname(url, 'feed')) or url
                result = await Feed.add_feed(self, jid_bare, db_file, url,
                                             identifier)
                if isinstance(result, list):
                    results = result
                    message = "Syndication feeds found for {}\n\n```\n".format(url)
                    for result in results:
                        message += ("Title : {}\n"
                                    "Link  : {}\n"
                                    "\n"
                                    .format(result['name'], result['link']))
                    message += '```\nTotal of {} feeds.'.format(len(results))
                elif result['exist']:
                    message = ('> {}\nNews source "{}" is already '
                               'listed in the subscription list at '
                               'index {}'
                               .format(result['link'],
                                       result['name'],
                                       result['index']))
                elif result['identifier']:
                    message = ('> {}\nIdentifier "{}" is already '
                               'allocated to index {}'
                               .format(result['link'],
                                       result['identifier'],
                                       result['index']))
                elif result['error']:
                    message = ('> {}\nFailed to find subscriptions.  '
                               'Reason: {} (status code: {})'
                               .format(url, result['message'],
                                       result['code']))
                else:
                    message = ('> {}\nNews source "{}" has been '
                               'added to subscription list.'
                               .format(result['link'], result['name']))
                # task.clean_tasks_xmpp_chat(self, jid_bare, ['status'])
                del self.pending_tasks[jid_bare][pending_tasks_num]
                # del self.pending_tasks[jid_bare][self.pending_tasks_counter]
                print(self.pending_tasks)
                XmppStatusTask.restart_task(self, jid_bare)
                # except:
                #     response = (
                #         '> {}\nNews source is in the process '
                #         'of being added to the subscription '
                #         'list.'.format(url)
                #         )
            else:
                message = ('No action has been taken.'
                           '\n'
                           'JID may not include "/".')
        else:
            message = ('No action has been taken.'
                       '\n'
                       'Missing argument. '
                       'Enter PubSub JID and subscription URL '
                       '(and optionally: Identifier Name).')
        return message

    # TODO Add dict and different result type to handle this function with
    # both interfaces Chat and IPC
    async def fetch_http(self, url, db_file, jid_bare):
        if url.startswith('feed:/') or url.startswith('rss:/'):
            url = uri.feed_to_http(url)
        url = (await uri.replace_hostname(url, 'feed')) or url
        counter = 0
        hostname = uri.get_hostname(url)
        hostname = hostname.replace('.','-')
        identifier = hostname + ':' + str(counter)
        while True:
            if sqlite.check_identifier_exist(db_file, identifier):
                counter += 1
                identifier = hostname + ':' + str(counter)
            else:
                break
        # try:
        result = await Feed.add_feed(self, jid_bare, db_file, url, identifier)
        if isinstance(result, list):
            results = result
            message = ("Syndication feeds found for {}\n\n```\n"
                       .format(url))
            for result in results:
                message += ("Title : {}\n"
                            "Link  : {}\n"
                            "\n"
                            .format(result['name'], result['link']))
            message += ('```\nTotal of {} feeds.'
                        .format(len(results)))
        elif result['exist']:
            message = ('> {}\nNews source "{}" is already '
                       'listed in the subscription list at '
                       'index {}'.format(result['link'],
                                         result['name'],
                                         result['index']))
        elif result['error']:
            message = ('> {}\nFailed to find subscriptions.  '
                       'Reason: {} (status code: {})'
                       .format(url, result['message'],
                               result['code']))
        else:
            message = ('> {}\nNews source "{}" has been '
                       'added to subscription list.'
                       .format(result['link'], result['name']))
        # except:
        #     response = (
        #         '> {}\nNews source is in the process '
        #         'of being added to the subscription '
        #         'list.'.format(url)
        #         )
        return message


    def list_feeds(db_file, query=None):
        if query:
            feeds = sqlite.search_feeds(db_file, query)
        else:
            feeds = sqlite.get_feeds(db_file)
        number = len(feeds)
        message = ''
        if number:
            for id, title, url in feeds:
                message += ('\nName : {} [{}]'
                            '\nURL  : {}'
                            '\n'
                            .format(str(title), str(id), str(url)))
        elif query:
            message = "No feeds were found for: {}".format(query)
        else:
            url = Utilities.pick_a_feed()
            message = ('List of subscriptions is empty. '
                       'To add a feed, send a URL.\n'
                       'Featured news: *{}*\n{}'
                       .format(url['name'], url['link']))
        return message, number


    def get_interval(self, jid_bare):
        result = Config.get_setting_value(
            self.settings, jid_bare, 'interval')
        message = str(result)
        return message


    async def set_interval(self, db_file, jid_bare, val):
        try:
            val_new = int(val)
            val_old = Config.get_setting_value(
                self.settings, jid_bare, 'interval')
            await Config.set_setting_value(
                self.settings, jid_bare, db_file, 'interval', val_new)
            message = ('Updates will be sent every {} minutes '
                       '(was: {}).'.format(val_new, val_old))
        except Exception as e:
            logger.error(str(e))
            message = ('No action has been taken.  Enter a numeric value only.')
        return message


    async def muc_leave(self, jid_bare):
        XmppMuc.leave(self, jid_bare)
        await XmppBookmark.remove(self, jid_bare)


    async def muc_join(self, command):
        if command:
            muc_jid = uri.check_xmpp_uri(command)
            if muc_jid:
                # TODO probe JID and confirm it's a groupchat
                result = await XmppMuc.join(self, muc_jid)
                # await XmppBookmark.add(self, jid=muc_jid)
                if result == 'ban':
                    message = '{} is banned from {}'.format(self.alias, muc_jid)
                else:
                    await XmppBookmark.add(self, muc_jid)
                    message = 'Joined groupchat {}'.format(muc_jid)
            else:
                message = '> {}\nGroupchat JID appears to be invalid.'.format(muc_jid)
        else:
            message = '> {}\nGroupchat JID is missing.'
        return message


    def get_length(self, jid_bare):
        result = Config.get_setting_value(
            self.settings, jid_bare, 'length')
        result = str(result)
        return result


    async def set_length(self, db_file, jid_bare, val):
        try:
            val_new = int(val)
            val_old = Config.get_setting_value(
                self.settings, jid_bare, 'length')
            await Config.set_setting_value(
                self.settings, jid_bare, db_file, 'length', val_new)
            if not val_new: # i.e. val_new == 0
                # TODO Add action to disable limit
                message = ('Summary length limit is disabled '
                           '(was: {}).'.format(val_old))
            else:
                message = ('Summary maximum length is set to '
                           '{} characters (was: {}).'
                           .format(val_new, val_old))
        except:
            message = ('No action has been taken.'
                       '\n'
                       'Enter a numeric value only.')
        return message


    async def set_media_off(self, jid_bare, db_file):
        await Config.set_setting_value(self.settings, jid_bare, db_file, 'media', 0)
        message = 'Media is disabled.'
        return message


    async def set_media_on(self, jid_bare, db_file):
        await Config.set_setting_value(self.settings, jid_bare, db_file, 'media', 1)
        message = 'Media is enabled.'
        return message


    async def set_old_off(self, jid_bare, db_file):
        await Config.set_setting_value(self.settings, jid_bare, db_file, 'old', 0)
        message = 'Only new items of newly added feeds be delivered.'
        return message


    async def set_old_on(self, jid_bare, db_file):
        await Config.set_setting_value(self.settings, jid_bare, db_file, 'old', 1)
        message = 'All items of newly added feeds be delivered.'
        return message


    def node_delete(self, info):
        info = info.split(' ')
        if len(info) > 2:
            jid = info[0]
            nid = info[1]
            if jid:
                XmppPubsub.delete_node(self, jid, nid)
                message = 'Deleted node: {}'.format(nid)
            else:
                message = 'PubSub JID is missing. Enter PubSub JID.'
        else:
            message = ('No action has been taken.'
                       '\n'
                       'Missing argument. '
                       'Enter JID and Node name.')
        return message


    def node_purge(self, info):
        info = info.split(' ')
        if len(info) > 1:
            jid = info[0]
            nid = info[1]
            if jid:
                XmppPubsub.purge_node(self, jid, nid)
                message = 'Purged node: {}'.format(nid)
            else:
                message = 'PubSub JID is missing. Enter PubSub JID.'
        else:
            message = ('No action has been taken.'
                       '\n'
                       'Missing argument. '
                       'Enter JID and Node name.')
        return message


    def print_options(self, jid_bare):
        message = ''
        for key in self.settings[jid_bare]:
            val = Config.get_setting_value(self.settings, jid_bare, key)
            # val = Config.get_setting_value(self.settings, jid_bare, key)
            steps = 11 - len(key)
            pulse = ''
            for step in range(steps):
                pulse += ' '
            message += '\n' + key + pulse + ': ' + str(val)
        return message


    def get_quantum(self, jid_bare):
        result = Config.get_setting_value(
            self.settings, jid_bare, 'quantum')
        message = str(result)
        return message


    async def set_quantum(self, db_file, jid_bare, val):
        try:
            val_new = int(val)
            val_old = Config.get_setting_value(
                self.settings, jid_bare, 'quantum')
            # response = (
            #     'Every update will contain {} news items.'
            #     ).format(response)
            db_file = config.get_pathname_to_database(jid_bare)
            await Config.set_setting_value(self.settings, jid_bare,
                                           db_file, 'quantum', val_new)
            message = ('Next update will contain {} news items (was: {}).'
                       .format(val_new, val_old))
        except:
            message = 'No action has been taken.  Enter a numeric value only.'
        return message


    # TODO
    def set_random(self, jid_bare, db_file):
        # TODO /questions/2279706/select-random-row-from-a-sqlite-table
        # NOTE sqlitehandler.get_entry_unread
        message = 'Updates will be sent by random order.'
        return message


    async def feed_read(self, jid_bare, data, url):
        if url.startswith('feed:/') or url.startswith('rss:/'):
            url = uri.feed_to_http(url)
        url = (await uri.replace_hostname(url, 'feed')) or url
        match len(data):
            case 1:
                if url.startswith('http'):
                    while True:
                        result = await fetch.http(url)
                        status = result['status_code']
                        if not result['error']:
                            document = result['content']
                            feed = parse(document)
                            if Feed.is_feed(url, feed):
                                message = Feed.view_feed(url, feed)
                                break
                            else:
                                result = await crawl.probe_page(url, document)
                                if isinstance(result, list):
                                    results = result
                                    message = ("Syndication feeds found for {}\n\n```\n"
                                               .format(url))
                                    for result in results:
                                        message += ("Title : {}\n"
                                                    "Link  : {}\n"
                                                    "\n"
                                                    .format(result['name'], result['link']))
                                    message += ('```\nTotal of {} feeds.'
                                               .format(len(results)))
                                    break
                                else:
                                    url = result['link']
                        else:
                            message = ('> {}\nFailed to load URL.  Reason: {}'
                                       .format(url, status))
                            break
                else:
                    message = ('No action has been taken.'
                               '\n'
                               'Missing URL.')
            case 2:
                num = data[1]
                if url.startswith('http'):
                    while True:
                        result = await fetch.http(url)
                        if not result['error']:
                            document = result['content']
                            status = result['status_code']
                            feed = parse(document)
                            if Feed.is_feed(url, feed):
                                message = Feed.view_entry(url, feed, num)
                                break
                            else:
                                result = await crawl.probe_page(url, document)
                                if isinstance(result, list):
                                    results = result
                                    message = ("Syndication feeds found for {}\n\n```\n"
                                               .format(url))
                                    for result in results:
                                        message += ("Title : {}\n"
                                                    "Link  : {}\n"
                                                    "\n"
                                                    .format(result['name'], result['link']))
                                    message += ('```\nTotal of {} feeds.'
                                                .format(len(results)))
                                    break
                                else:
                                    url = result['link']
                        else:
                            message = ('> {}\nFailed to load URL.  Reason: {}'
                                       .format(url, status))
                            break
                else:
                    message = ('No action has been taken.'
                               '\n'
                               'Missing URL.')
            case _:
                message = ('Enter command as follows:\n'
                           '`read <url>` or `read <url> <number>`\n'
                           'URL must not contain white space.')
        return message


    def print_recent(self, db_file, num):
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: num: {}'
                    .format(function_name, num))
        try:
            num = int(num)
            if num < 1 or num > 50:
                message = 'Value must be ranged from 1 to 50.'
            else:
                result = sqlite.get_last_entries(db_file, num)
                count = len(result)
                message = ''
                for i in result:
                    title, url, date = i
                    message += ('\n{}\n{}\n'.format(title, url))
        except Exception as e:
            logger.error(str(e))
            count = False
            message = 'No action has been taken.  Enter a numeric value only.'
        return count, message


    async def feed_remove(self, jid_bare, db_file, ix_url):
        if ix_url:
            sub_removed = []
            url_invalid = []
            ixs_invalid = []
            message = 'Result:\n```'
            for i in ix_url:
                if i:
                    try:
                        ix = int(i)
                        url = sqlite.get_feed_url(db_file, ix)
                        if url:
                            url = url[0]
                            # name = sqlite.get_feed_title(db_file, ix)
                            # name = name[0]
                            await sqlite.remove_feed_by_index(db_file, ix)
                            sub_removed.append(url)
                        else:
                            ixs_invalid.append(str(ix))
                    except:
                        url = i
                        feed_id = sqlite.get_feed_id(db_file, url)
                        if feed_id:
                            feed_id = feed_id[0]
                            await sqlite.remove_feed_by_index(db_file, feed_id)
                            # await sqlite.remove_feed_by_url(db_file, url)
                            sub_removed.append(url)
                        else:
                            url_invalid.append(url)
            if len(sub_removed):
                message += '\nThe following subscriptions have been removed:\n\n'
                for url in sub_removed:
                    message += '{}\n'.format(url)
            if len(url_invalid):
                urls = ', '.join(url_invalid)
                message += '\nThe following URLs do not exist:\n\n{}\n'.format(urls)
            if len(ixs_invalid):
                ixs = ', '.join(ixs_invalid)
                message += '\nThe following indexes do not exist:\n\n{}\n'.format(ixs)
            message += '\n```'
        else:
            message = ('No action has been taken.'
                        '\n'
                        'Missing argument. '
                        'Enter a subscription URL or index number.')
        return message


    async def mark_as_read(jid_bare, db_file, ix_url=None):
        if ix_url:
            sub_marked = []
            url_invalid = []
            ixs_invalid = []
            message = 'Result:\n```'
            for i in ix_url:
                if i:
                    try:
                        ix = int(i)
                        url = sqlite.get_feed_url(db_file, ix)
                        if url:
                            url = url[0]
                            # name = sqlite.get_feed_title(db_file, ix)
                            # name = name[0]
                            await sqlite.mark_feed_as_read(db_file, ix)
                            sub_marked.append(url)
                        else:
                            ixs_invalid.append(str(ix))
                    except:
                        url = i
                        feed_id = sqlite.get_feed_id(db_file, url)
                        if feed_id:
                            feed_id = feed_id[0]
                            await sqlite.mark_feed_as_read(db_file, feed_id)
                            sub_marked.append(url)
                        else:
                            url_invalid.append(url)
            if len(sub_marked):
                message += '\nThe following subscriptions have been marked as read:\n\n'
                for url in sub_marked:
                    message += '{}\n'.format(url)
            if len(url_invalid):
                urls = ', '.join(url_invalid)
                message += '\nThe following URLs do not exist:\n\n{}\n'.format(urls)
            if len(ixs_invalid):
                ixs = ', '.join(ixs_invalid)
                message += '\nThe following indexes do not exist:\n\n{}\n'.format(ixs)
            message += '\n```'
        else:
            await sqlite.mark_all_as_read(db_file)
            message = 'All subscriptions have been marked as read.'
        return message


    async def search_items(db_file, query):
        if query:
            if len(query) > 3:
                results = sqlite.search_entries(db_file, query)
                message = ("Search results for '{}':\n\n```"
                           .format(query))
                for result in results:
                    message += ("\n{}\n{}\n"
                                .format(str(result[0]), str(result[1])))
                if len(results):
                    message += "```\nTotal of {} results".format(len(results))
                else:
                    message = "No results were found for: {}".format(query)
            else:
                message = 'Enter at least 4 characters to search'
        else:
            message = ('No action has been taken.'
                        '\n'
                        'Missing search query.')
        return message


    # Tasks are classes which are passed to this function
    # On an occasion in which they would have returned, variable "tasks" might be called "callback"
    async def scheduler_start(self, db_file, jid_bare, tasks):
        await Config.set_setting_value(self.settings, jid_bare, db_file, 'enabled', 1)
        for task in tasks:
            task.restart_task(self, jid_bare)
        message = 'Updates are enabled.'
        return message


    async def scheduler_stop(self, db_file, jid_bare):
        await Config.set_setting_value(
            self.settings, jid_bare, db_file, 'enabled', 0)
        for task in ('interval', 'status'):
            if (jid_bare in self.task_manager and
                task in self.task_manager[jid_bare]):
                self.task_manager[jid_bare][task].cancel()
            else:
                logger.debug('No task {} for JID {} (Task.stop)'
                             .format(task, jid_bare))
        message = 'Updates are disabled.'
        return message


    # """You have {} unread news items out of {} from {} news sources.
    # """.format(unread_entries, entries, feeds)
    def print_statistics(db_file):
        """
        Print statistics.
    
        Parameters
        ----------
        db_file : str
            Path to database file.
    
        Returns
        -------
        msg : str
            Statistics as message.
        """
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: db_file: {}'
                    .format(function_name, db_file))
        entries_unread = sqlite.get_number_of_entries_unread(db_file)
        entries = sqlite.get_number_of_items(db_file, 'entries_properties')
        feeds_active = sqlite.get_number_of_feeds_active(db_file)
        feeds_all = sqlite.get_number_of_items(db_file, 'feeds_properties')
        message = ("Statistics:"
                   "\n"
                   "```"
                   "\n"
                   "News items   : {}/{}\n"
                   "News sources : {}/{}\n"
                   "```").format(entries_unread,
                                 entries,
                                 feeds_active,
                                 feeds_all)
        return message


    async def feed_disable(self, db_file, jid_bare, command):
        feed_id = command[8:]
        try:
            await sqlite.set_enabled_status(db_file, feed_id, 0)
            await sqlite.mark_feed_as_read(db_file, feed_id)
            name = sqlite.get_feed_title(db_file, feed_id)
            name = name[0]
            addr = sqlite.get_feed_url(db_file, feed_id)
            addr = addr[0]
            message = ('Updates are now disabled for subscription:\n{}\n{}'
                       .format(addr, name))
        except:
            message = ('No action has been taken.  No news source with index {}.'
                       .format(feed_id))
        XmppStatusTask.restart_task(self, jid_bare)
        return message


    async def feed_enable(self, db_file, command):
        feed_id = command[7:]
        try:
            await sqlite.set_enabled_status(db_file, feed_id, 1)
            name = sqlite.get_feed_title(db_file, feed_id)[0]
            addr = sqlite.get_feed_url(db_file, feed_id)[0]
            message = ('> {}\n'
                        'Updates are now enabled for news source "{}"'
                        .format(addr, name))
        except:
            message = ('No action has been taken.'
                        '\n'
                        'No news source with index {}.'.format(feed_id))
        return message


    async def feed_rename(self, db_file, jid_bare, command):
        command = command[7:]
        feed_id = command.split(' ')[0]
        name = ' '.join(command.split(' ')[1:])
        if name:
            try:
                feed_id = int(feed_id)
                name_old = sqlite.get_feed_title(db_file, feed_id)
                if name_old:
                    name_old = name_old[0]
                    if name == name_old:
                        message = ('No action has been taken.'
                                   '\n'
                                   'Input name is identical to the '
                                   'existing name.')
                    else:
                        await sqlite.set_feed_title(db_file, feed_id,
                                                    name)
                        message = ('> {}'
                                   '\n'
                                   'Subscription #{} has been '
                                   'renamed to "{}".'.format(
                                       name_old,feed_id, name))
                else:
                    message = 'Subscription with Id {} does not exist.'.format(feed_id)
            except:
                message = ('No action has been taken.'
                           '\n'
                           'Subscription Id must be a numeric value.')
        else:
            message = ('No action has been taken.'
                       '\n'
                       'Missing argument. '
                       'Enter subscription Id and name.')
        return message


    def print_support_jid():
        muc_jid = 'slixfeed@chat.woodpeckersnest.space'
        message = 'Join xmpp:{}?join'.format(muc_jid)
        return message
        
    async def invite_jid_to_muc(self, jid_bare):
        muc_jid = 'slixfeed@chat.woodpeckersnest.space'
        if await XmppUtilities.get_chat_type(self, jid_bare) == 'chat':
            self.plugin['xep_0045'].invite(muc_jid, jid_bare)


    def print_version():
        message = __version__
        return message


    def print_unknown():
        message = 'An unknown command.  Type "help" for a list of commands.'
        return message
