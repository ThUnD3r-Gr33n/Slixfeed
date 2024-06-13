#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

TODO

1) Function scan at "for entry in entries"
   Suppress directly calling function "add_entry" (accept db_file)
   Pass a list of valid entries to a new function "add_entries"
   (accept db_file) which would call function "add_entry" (accept cur).
   * accelerate adding of large set of entries at once.
   * prevent (or mitigate halt of consequent actions).
   * reduce I/O.

2) Call sqlite function from function statistics.
   Returning a list of values doesn't' seem to be a good practice.

3) Special statistics for operator:
   * Size of database(s);
   * Amount of JIDs subscribed;
   * Amount of feeds of all JIDs;
   * Amount of entries of all JIDs.

4) Consider to append text to remind to share presence
    '✒️ Share online status to receive updates'

5) Request for subscription
   if (await XmppUtilities.get_chat_type(self, jid_bare) == 'chat' and
       not self.client_roster[jid_bare]['to']):
       XmppPresence.subscription(self, jid_bare, 'subscribe')
       await XmppRoster.add(self, jid_bare)
       status_message = '✒️ Share online status to receive updates'
       XmppPresence.send(self, jid_bare, status_message)
       message_subject = 'RSS News Bot'
       message_body = 'Share online status to receive updates.'
       XmppMessage.send_headline(self, jid_bare, message_subject,
                                 message_body, 'chat')

"""

import hashlib
import slixfeed.config as config
from slixfeed.config import Config
from lxml import etree, html
import slixfeed.dt as dt
import slixfeed.fetch as fetch
from slixfeed.log import Logger
import slixfeed.sqlite as sqlite
from slixfeed.url import join_url, complete_url
import sys

try:
    import tomllib
except:
    import tomli as tomllib

logger = Logger(__name__)


class Documentation:


    def manual(filename, section=None, command=None):
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: filename: {}'.format(function_name, filename))
        config_dir = config.get_default_config_directory()
        with open(config_dir + '/' + filename, mode="rb") as commands:
            cmds = tomllib.load(commands)
        if section == 'all':
            cmd_list = ''
            for cmd in cmds:
                for i in cmds[cmd]:
                    cmd_list += cmds[cmd][i] + '\n'
        elif command and section:
            try:
                cmd_list = cmds[section][command]
            except KeyError as e:
                logger.error(e)
                cmd_list = None
        elif section:
            try:
                cmd_list = []
                for cmd in cmds[section]:
                    cmd_list.extend([cmd])
            except KeyError as e:
                logger.error('KeyError:' + str(e))
                cmd_list = None
        else:
            cmd_list = []
            for cmd in cmds:
                cmd_list.extend([cmd])
        return cmd_list


class Html:


    async def extract_image_from_html(url):
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: url: {}'.format(function_name, url))
        result = await fetch.http(url)
        if not result['error']:
            data = result['content']
            tree = html.fromstring(data)
            # TODO Exclude banners, class="share" links etc.
            images = tree.xpath(
                '//img[not('
                    'contains(@src, "avatar") or '
                    'contains(@src, "cc-by-sa") or '
                    'contains(@src, "emoji") or '
                    'contains(@src, "icon") or '
                    'contains(@src, "logo") or '
                    'contains(@src, "letture") or '
                    'contains(@src, "poweredby_mediawi") or '
                    'contains(@src, "search") or '
                    'contains(@src, "share") or '
                    'contains(@src, "smiley")'
                ')]/@src')
            if len(images):
                image = images[0]
                image = str(image)
                image_url = complete_url(url, image)
                return image_url


    def remove_html_tags(data):
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}'.format(function_name))
        parser = etree.HTMLParser()
        tree = etree.fromstring(data, parser)
        data = etree.tostring(tree, encoding='unicode', method='text')
        data = data.replace("\n\n", "\n")
        return data


    # /questions/9662346/python-code-to-remove-html-tags-from-a-string
    def _remove_html_tags(text):
        import xml.etree.ElementTree
        return ''.join(xml.etree.ElementTree.fromstring(text).itertext())


    def __remove_html_tags(data):
        from bs4 import BeautifulSoup
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}'.format(function_name))
        data = BeautifulSoup(data, "lxml").text
        data = data.replace("\n\n", "\n")
        return data


class MD:


    def export_to_markdown(jid, filename, results):
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid: {} filename: {}'
                    .format(function_name, jid, filename))
        with open(filename, 'w') as file:
            file.write('# Subscriptions for {}\n'.format(jid))
            file.write('## Set of feeds exported with Slixfeed\n')
            for result in results:
                file.write('- [{}]({})\n'.format(result[1], result[2]))
            file.write('\n\n* * *\n\nThis list was saved on {} from xmpp:{} using '
                       '[Slixfeed](https://slixfeed.woodpeckersnest.space/)\n'
                       .format(dt.current_date(), jid))


    def log_to_markdown(timestamp, filename, jid, message):
        """
        Log message to a markdown file.
    
        Parameters
        ----------
        timestamp : str
            Time stamp.
        filename : str
            Jabber ID as name of file.
        jid : str
            Jabber ID.
        message : str
            Message content.
    
        Returns
        -------
        None.
        
        """
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: timestamp: {} filename: {} jid: {} message: {}'.format(function_name, timestamp, filename, jid, message))
        with open(filename + '.md', 'a') as file:
            # entry = "{} {}:\n{}\n\n".format(timestamp, jid, message)
            entry = '## {}\n### {}\n\n{}\n\n'.format(jid, timestamp, message)
            file.write(entry)


class SQLiteMaintain:


    # TODO
    # (1) Check for duplications
    # (2) append all duplications to a list
    # (3) Send the list to a function in module sqlite.
    async def remove_nonexistent_entries(self, jid_bare, db_file, url, feed):
        """
        Remove entries that don't exist in a given parsed feed.
        Check the entries returned from feed and delete read non
        existing entries, otherwise move to table archive, if unread.
    
        Parameters
        ----------
        db_file : str
            Path to database file.
        url : str
            Feed URL.
        feed : list
            Parsed feed document.
        """
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: db_file: {} url: {}'
                    .format(function_name, db_file, url))
        feed_id = sqlite.get_feed_id(db_file, url)
        feed_id = feed_id[0]
        items = sqlite.get_entries_of_feed(db_file, feed_id)
        entries = feed.entries
        limit = Config.get_setting_value(self.settings, jid_bare, 'archive')
        print(limit)
        for item in items:
            ix, entry_title, entry_link, entry_id, timestamp = item
            read_status = sqlite.is_entry_read(db_file, ix)
            read_status = read_status[0]
            valid = False
            for entry in entries:
                title = None
                link = None
                time = None
                # valid = False
                # TODO better check and don't repeat code
                if entry.has_key("id") and entry_id:
                    if entry.id == entry_id:
                        print("compare entry.id == entry_id:", entry.id)
                        print("compare entry.id == entry_id:", entry_id)
                        print("============")
                        valid = True
                        break
                else:
                    if entry.has_key("title"):
                        title = entry.title
                    else:
                        title = feed["feed"]["title"]
                    if entry.has_key("link"):
                        link = join_url(url, entry.link)
                    else:
                        link = url
                    if entry.has_key("published") and timestamp:
                        print("compare published:", title, link, time)
                        print("compare published:", entry_title, entry_link, timestamp)
                        print("============")
                        time = dt.rfc2822_to_iso8601(entry.published)
                        if (entry_title == title and
                            entry_link == link and
                            timestamp == time):
                            valid = True
                            break
                    else:
                        if (entry_title == title and
                            entry_link == link):
                            print("compare entry_link == link:", title, link)
                            print("compare entry_title == title:", entry_title, entry_link)
                            print("============")
                            valid = True
                            break
                # TODO better check and don't repeat code
            if not valid:
                # print("id:        ", ix)
                # if title:
                #     print("title:     ", title)
                #     print("entry_title:   ", entry_title)
                # if link:
                #     print("link:      ", link)
                #     print("entry_link:   ", entry_link)
                # if entry.id:
                #     print("last_entry:", entry.id)
                #     print("entry_id:   ", entry_id)
                # if time:
                #     print("time:      ", time)
                #     print("timestamp:   ", timestamp)
                # print("read:      ", read_status)
                # breakpoint()
    
                # TODO Send to table archive
                # TODO Also make a regular/routine check for sources that
                #      have been changed (though that can only happen when
                #      manually editing)
                # ix = item[0]
                # print(">>> SOURCE: ", source)
                # print(">>> INVALID:", entry_title)
                # print("title:", entry_title)
                # print("link :", entry_link)
                # print("id   :", entry_id)
                if read_status == 1:
                    await sqlite.delete_entry_by_id(db_file, ix)
                    # print(">>> DELETING:", entry_title)
                else:
                    # print(">>> ARCHIVING:", entry_title)
                    await sqlite.archive_entry(db_file, ix)
            await sqlite.maintain_archive(db_file, limit)


"""

Consider utilizing a dict as a handler that would match task keyword to functions.

tasks_xmpp_chat =  {"check" : check_updates,
                    "status" : task_status_message,
                    "interval" : task_message}

tasks_xmpp_pubsub =  {"check" : check_updates,
                      "pubsub" : task_pubsub}

"""


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


class Utilities:


    # NOTE Warning: Entry might not have a link
    # TODO Handle situation error
    def hash_url_to_md5(url):
        url_encoded = url.encode()
        url_hashed = hashlib.md5(url_encoded)
        url_digest = url_hashed.hexdigest()
        return url_digest


    def pick_a_feed(lang=None):
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: lang: {}'
                    .format(function_name, lang))
        config_dir = config.get_default_config_directory()
        with open(config_dir + '/' + 'feeds.toml', mode="rb") as feeds:
            urls = tomllib.load(feeds)
        import random
        url = random.choice(urls['feeds'])
        return url
