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

"""

# import asyncio
from asyncio.exceptions import IncompleteReadError
from bs4 import BeautifulSoup
from feedparser import parse
from http.client import IncompleteRead
import json
from slixfeed.log import Logger
from lxml import html
import os
import slixfeed.config as config
from slixfeed.config import Config
import slixfeed.crawl as crawl
import slixfeed.dt as dt
import slixfeed.fetch as fetch
import slixfeed.sqlite as sqlite
import slixfeed.url as uri
from slixfeed.url import (
    complete_url,
    join_url,
    remove_tracking_parameters,
    replace_hostname,
    trim_url
    )
import slixfeed.task as task
from slixfeed.xmpp.bookmark import XmppBookmark
from slixfeed.xmpp.iq import XmppIQ
from slixfeed.xmpp.message import XmppMessage
from slixfeed.xmpp.presence import XmppPresence
from slixfeed.xmpp.publish import XmppPubsub
from slixfeed.xmpp.upload import XmppUpload
from slixfeed.xmpp.utility import get_chat_type
import sys
from urllib import error
from urllib.parse import parse_qs, urlsplit
import xml.etree.ElementTree as ET

try:
    import tomllib
except:
    import tomli as tomllib

logger = Logger(__name__)

try:
    import xml2epub
except ImportError:
    logger.error('Package xml2epub was not found.\n'
                 'ePUB support is disabled.')

try:
    import html2text
except ImportError:
    logger.error('Package html2text was not found.\n'
                 'Markdown support is disabled.')

try:
    import pdfkit
except ImportError:
    logger.error('Package pdfkit was not found.\n'
                 'PDF support is disabled.')

try:
    from readability import Document
except ImportError:
    logger.error('Package readability was not found.\n'
                 'Arc90 Lab algorithm is disabled.')


async def export_feeds(self, jid, jid_file, ext):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: jid: {}: jid_file: {}: ext: {}'.format(function_name, jid, jid_file, ext))
    cache_dir = config.get_default_cache_directory()
    if not os.path.isdir(cache_dir):
        os.mkdir(cache_dir)
    if not os.path.isdir(cache_dir + '/' + ext):
        os.mkdir(cache_dir + '/' + ext)
    filename = os.path.join(
        cache_dir, ext, 'slixfeed_' + dt.timestamp() + '.' + ext)
    db_file = config.get_pathname_to_database(jid_file)
    results = sqlite.get_feeds(db_file)
    match ext:
        # case 'html':
        #     response = 'Not yet implemented.'
        case 'md':
            export_to_markdown(jid, filename, results)
        case 'opml':
            export_to_opml(jid, filename, results)
        # case 'xbel':
        #     response = 'Not yet implemented.'
    return filename


"""
TODO

Consider to append text to remind to share presence
'✒️ Share online status to receive updates'

# TODO Request for subscription
if (await get_chat_type(self, jid_bare) == 'chat' and
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

async def xmpp_send_status_message(self, jid):
    """
    Send status message.

    Parameters
    ----------
    jid : str
        Jabber ID.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: jid: {}'.format(function_name, jid))
    status_text = '📜️ Slixfeed RSS News Bot'
    jid_file = jid.replace('/', '_')
    db_file = config.get_pathname_to_database(jid_file)
    enabled = Config.get_setting_value(self.settings, jid, 'enabled')
    if not enabled:
        status_mode = 'xa'
        status_text = '📪️ Send "Start" to receive updates'
    else:
        jid_task = self.pending_tasks[jid]
        if len(jid_task):
            status_mode = 'dnd'
            status_text = jid_task[list(jid_task.keys())[0]]
        else:
            feeds = sqlite.get_number_of_items(db_file, 'feeds')
            # print(await current_time(), jid, "has", feeds, "feeds")
            if not feeds:
                status_mode = 'available'
                status_text = '📪️ Send a URL from a blog or a news website'
            else:
                unread = sqlite.get_number_of_entries_unread(db_file)
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
    XmppPresence.send(self, jid, status_text, status_type=status_mode)
    # await asyncio.sleep(60 * 20)
    # await refresh_task(self, jid, send_status, 'status', '90')
    # loop.call_at(
    #     loop.time() + 60 * 20,
    #     loop.create_task,
    #     send_status(jid)
    # )


async def xmpp_send_pubsub(self, jid_bare):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: jid_bare: {}'.format(function_name, jid_bare))
    jid_file = jid_bare.replace('/', '_')
    db_file = config.get_pathname_to_database(jid_file)
    enabled = Config.get_setting_value(self.settings, jid_bare, 'enabled')
    if enabled:
        subscriptions = sqlite.get_active_feeds_url(db_file)
        for url in subscriptions:
            url = url[0]
            feed_id = sqlite.get_feed_id(db_file, url)
            feed_id = feed_id[0]
            feed_title = sqlite.get_feed_title(db_file, feed_id)
            feed_title = feed_title[0]
            feed_summary = None
            node = sqlite.get_node_name(db_file, feed_id)
            node = node[0]
            xep = None
            iq_create_node = XmppPubsub.create_node(
                self, jid_bare, node, xep, feed_title, feed_summary)
            await XmppIQ.send(self, iq_create_node)
            entries = sqlite.get_unread_entries_of_feed(db_file, feed_id)
            feed_properties = sqlite.get_feed_properties(db_file, feed_id)
            feed_version = feed_properties[2]
            for entry in entries:
                feed_entry = {'author'      : None,
                              'authors'     : None,
                              'category'    : None,
                              'content'     : None,
                              'description' : entry[3],
                              'href'        : entry[2],
                              'links'       : entry[4],
                              'tags'        : None,
                              'title'       : entry[1],
                              'type'        : None,
                              'updated'     : entry[7]}
                iq_create_entry = XmppPubsub.create_entry(
                    self, jid_bare, node, feed_entry, feed_version)
                await XmppIQ.send(self, iq_create_entry)
                ix = entry[0]
                await sqlite.mark_as_read(db_file, ix)


async def xmpp_send_message(self, jid, num=None):
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
    logger.debug('{}: jid: {} num: {}'.format(function_name, jid, num))
    jid_file = jid.replace('/', '_')
    db_file = config.get_pathname_to_database(jid_file)
    enabled = Config.get_setting_value(self.settings, jid, 'enabled')
    if enabled:
        show_media = Config.get_setting_value(self.settings, jid, 'media')
        if not num:
            num = Config.get_setting_value(self.settings, jid, 'quantum')
        else:
            num = int(num)
        results = sqlite.get_unread_entries(db_file, num)
        news_digest = ''
        media = None
        chat_type = await get_chat_type(self, jid)
        for result in results:
            ix = result[0]
            title_e = result[1]
            url = result[2]
            summary = result[3]
            enclosure = result[4]
            feed_id = result[5]
            date = result[6]
            title_f = sqlite.get_feed_title(db_file, feed_id)
            title_f = title_f[0]
            news_digest += list_unread_entries(self, result, title_f, jid)
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
                    media = await extract_image_from_html(url)
            
            if media and news_digest:
                # Send textual message
                XmppMessage.send(self, jid, news_digest, chat_type)
                news_digest = ''
                # Send media
                XmppMessage.send_oob(self, jid, media, chat_type)
                media = None
                
        if news_digest:
            XmppMessage.send(self, jid, news_digest, chat_type)
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

        # await start_tasks_xmpp_chat(self, jid, ['status'])
        # await refresh_task(self, jid, send_update, 'interval')

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
            logger.error(str(e))
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


def log_to_markdown(timestamp, filename, jid, message):
    """
    Log message to file.

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
        entry = (
        "## {}\n"
        "### {}\n\n"
        "{}\n\n").format(jid, timestamp, message)
        file.write(entry)


def is_feed_json(document):
    """

    NOTE /kurtmckee/feedparser/issues/103

    Determine whether document is json feed or not.

    Parameters
    ----------
    feed : dict
        Parsed feed.

    Returns
    -------
    val : boolean
        True or False.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}'.format(function_name))
    value = False
    try:
        feed = json.loads(document)
        if not feed['items']:
            if "version" in feed.keys():
                if 'jsonfeed' in feed['version']:
                    value = True
                else: # TODO Test
                    value = False
            # elif 'title' in feed.keys():
            #     value = True
            else:
                value = False
        else:
            value = True
    except:
        pass
    return value


def is_feed(feed):
    """
    Determine whether document is feed or not.

    Parameters
    ----------
    feed : dict
        Parsed feed.

    Returns
    -------
    val : boolean
        True or False.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}'.format(function_name))
    value = False
    # message = None
    if not feed.entries:
        if "version" in feed.keys():
            # feed["version"]
            if feed.version:
                value = True
                # message = (
                #     "Empty feed for {}"
                #     ).format(url)
        elif "title" in feed["feed"].keys():
            value = True
            # message = (
            #     "Empty feed for {}"
            #     ).format(url)
        else:
            value = False
            # message = (
            #     "No entries nor title for {}"
            #     ).format(url)
    elif feed.bozo:
        value = False
        # message = (
        #     "Bozo detected for {}"
        #     ).format(url)
    else:
        value = True
        # message = (
        #     "Good feed for {}"
        #     ).format(url)
    return value


def list_unread_entries(self, result, feed_title, jid):
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
    title = str(result[1])
    # # TODO Retrieve summary from feed
    # # See fetch.view_entry
    summary = result[3]
    # Remove HTML tags
    try:
        title = BeautifulSoup(title, "lxml").text
        summary = BeautifulSoup(summary, "lxml").text
    except:
        print(result[3])
        breakpoint()
    # TODO Limit text length
    # summary = summary.replace("\n\n\n", "\n\n")
    summary = summary.replace('\n', ' ')
    summary = summary.replace('	', ' ')
    summary = summary.replace('  ', ' ')
    length = Config.get_setting_value(self.settings, jid, 'length')
    length = int(length)
    summary = summary[:length] + " […]"
    # summary = summary.strip().split('\n')
    # summary = ["> " + line for line in summary]
    # summary = "\n".join(summary)
    link = result[2]
    link = remove_tracking_parameters(link)
    link = (replace_hostname(link, "link")) or link
    # news_item = ("\n{}\n{}\n{} [{}]\n").format(str(title), str(link),
    #                                            str(feed_title), str(ix))
    formatting = Config.get_setting_value(self.settings, jid, 'formatting')
    news_item = formatting.format(feed_title=feed_title,
                                  title=title,
                                  summary=summary,
                                  link=link,
                                  ix=ix)
    # news_item = news_item.replace('\\n', '\n')
    return news_item


def list_search_results(query, results):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: query: {}'
                .format(function_name, query))
    message = ("Search results for '{}':\n\n```"
               .format(query))
    for result in results:
        message += ("\n{}\n{}\n"
                    .format(str(result[0]), str(result[1])))
    if len(results):
        message += "```\nTotal of {} results".format(len(results))
    else:
        message = "No results were found for: {}".format(query)
    return message


def list_feeds_by_query(query, results):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}'.format(function_name))
    message = ('Feeds containing "{}":\n\n```'
               .format(query))
    for result in results:
        message += ('\nName : {} [{}]'
                    '\nURL  : {}'
                    '\n'
                    .format(str(result[0]), str(result[1]), str(result[2])))
    if len(results):
        message += "\n```\nTotal of {} feeds".format(len(results))
    else:
        message = "No feeds were found for: {}".format(query)
    return message


async def list_options(self, jid_bare):
    """
    Print options.

    Parameters
    ----------
    jid_bare : str
        Jabber ID.

    Returns
    -------
    msg : str
        Options as message.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: jid: {}'
                .format(function_name, jid_bare))

    # msg = """You have {} unread news items out of {} from {} news sources.
    #       """.format(unread_entries, entries, feeds)

    # try:
    #     value = cur.execute(sql, par).fetchone()[0]
    # except:
    #     print("Error for key:", key)
    #     value = "Default"
    # values.extend([value])

    value_archive = Config.get_setting_value(self.settings, jid_bare, 'archive')
    value_interval = Config.get_setting_value(self.settings, jid_bare, 'interval')
    value_quantum = Config.get_setting_value(self.settings, jid_bare, 'quantum')
    value_enabled = Config.get_setting_value(self.settings, jid_bare, 'enabled')

    message = ("Options:"
               "\n"
               "```"
               "\n"
               "Items to archive : {}\n"
               "Update interval  : {}\n"
               "Items per update : {}\n"
               "Operation status : {}\n"
               "```").format(value_archive, value_interval, value_quantum,
                             value_enabled)
    return message


async def list_statistics(db_file):
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
    entries = sqlite.get_number_of_items(db_file, 'entries')
    archive = sqlite.get_number_of_items(db_file, 'archive')
    entries_all = entries + archive
    feeds_active = sqlite.get_number_of_feeds_active(db_file)
    feeds_all = sqlite.get_number_of_items(db_file, 'feeds')

    # msg = """You have {} unread news items out of {} from {} news sources.
    #       """.format(unread_entries, entries, feeds)

    # try:
    #     value = cur.execute(sql, par).fetchone()[0]
    # except:
    #     print("Error for key:", key)
    #     value = "Default"
    # values.extend([value])

    message = ("Statistics:"
               "\n"
               "```"
               "\n"
               "News items   : {}/{}\n"
               "News sources : {}/{}\n"
               "```").format(entries_unread,
                             entries_all,
                             feeds_active,
                             feeds_all)
    return message


# FIXME Replace counter by len
def list_last_entries(results, num):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: num: {}'
                .format(function_name, num))
    message = "Recent {} titles:\n\n```".format(num)
    for result in results:
        message += ("\n{}\n{}\n"
                    .format(str(result[0]), str(result[1])))
    if len(results):
        message += "```\n"
    else:
        message = "There are no news at the moment."
    return message


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


def list_feeds(results):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}'.format(function_name))
    message = "\nList of subscriptions:\n\n```\n"
    for result in results:
        message += ("{} [{}]\n"
                    "{}\n"
                    "\n\n"
                    .format(str(result[1]), str(result[0]), str(result[2])))
    if len(results):
        message += ('```\nTotal of {} subscriptions.\n'
                    .format(len(results)))
    else:
        url = pick_a_feed()
        message = ('List of subscriptions is empty.'
                   '\n'
                   'To add a feed, send a URL.'
                   '\n'
                   'Featured news:\n*{}*\n{}'
                   .format(url['name'], url['link']))
    return message


async def list_bookmarks(self):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}'.format(function_name))
    conferences = await XmppBookmark.get(self)
    message = '\nList of groupchats:\n\n```\n'
    for conference in conferences:
        message += ('Name: {}\n'
                    'Room: {}\n'
                    '\n'
                    .format(conference['name'], conference['jid']))
    message += ('```\nTotal of {} groupchats.\n'
                .format(len(conferences)))
    return message


def export_to_markdown(jid, filename, results):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: jid: {} filename: {}'
                .format(function_name, jid, filename))
    with open(filename, 'w') as file:
        file.write('# Subscriptions for {}\n'.format(jid))
        file.write('## Set of feeds exported with Slixfeed\n')
        for result in results:
            file.write('- [{}]({})\n'.format(result[0], result[1]))
        file.write('\n\n* * *\n\nThis list was saved on {} from xmpp:{} using '
                   '[Slixfeed](https://gitgud.io/sjehuda/slixfeed)\n'
                   .format(dt.current_date(), jid))


# TODO Consider adding element jid as a pointer of import
def export_to_opml(jid, filename, results):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{} jid: {} filename: {}'
                .format(function_name, jid, filename))
    root = ET.Element("opml")
    root.set("version", "1.0")
    head = ET.SubElement(root, "head")
    ET.SubElement(head, "title").text = "{}".format(jid)
    ET.SubElement(head, "description").text = (
        "Set of subscriptions exported by Slixfeed")
    ET.SubElement(head, "generator").text = "Slixfeed"
    ET.SubElement(head, "urlPublic").text = (
        "https://gitgud.io/sjehuda/slixfeed")
    time_stamp = dt.current_time()
    ET.SubElement(head, "dateCreated").text = time_stamp
    ET.SubElement(head, "dateModified").text = time_stamp
    body = ET.SubElement(root, "body")
    for result in results:
        outline = ET.SubElement(body, "outline")
        outline.set("text", result[0])
        outline.set("xmlUrl", result[1])
        # outline.set("type", result[2])
    tree = ET.ElementTree(root)
    tree.write(filename)


async def import_opml(db_file, result):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {}'
                .format(function_name, db_file))
    if not result['error']:
        document = result['content']
        root = ET.fromstring(document)
        before = sqlite.get_number_of_items(db_file, 'feeds')
        feeds = []
        for child in root.findall(".//outline"):
            url = child.get("xmlUrl")
            title = child.get("text")
            # feed = (url, title)
            # feeds.extend([feed])
            feeds.extend([(url, title)])
        await sqlite.import_feeds(db_file, feeds)
        await sqlite.add_metadata(db_file)
        after = sqlite.get_number_of_items(db_file, 'feeds')
        difference = int(after) - int(before)
        return difference


async def add_feed(self, jid_bare, db_file, url, node):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} url: {}'
                .format(function_name, db_file, url))
    while True:
        exist_feed = sqlite.get_feed_id_and_name(db_file, url)
        if not exist_feed:
            exist_node = sqlite.check_node_exist(db_file, node)
            if not exist_node:
                result = await fetch.http(url)
                message = result['message']
                status_code = result['status_code']
                if not result['error']:
                    document = result['content']
                    feed = parse(document)
                    # if is_feed(url, feed):
                    if is_feed(feed):
                        if "title" in feed["feed"].keys():
                            title = feed["feed"]["title"]
                        else:
                            title = urlsplit(url).netloc
                        if "language" in feed["feed"].keys():
                            language = feed["feed"]["language"]
                        else:
                            language = ''
                        if "encoding" in feed.keys():
                            encoding = feed["encoding"]
                        else:
                            encoding = ''
                        if "updated_parsed" in feed["feed"].keys():
                            updated = feed["feed"]["updated_parsed"]
                            try:
                                updated = dt.convert_struct_time_to_iso8601(updated)
                            except:
                                updated = ''
                        else:
                            updated = ''
                        version = feed["version"]
                        entries = len(feed["entries"])
                        await sqlite.insert_feed(db_file, url, title, node,
                                                 entries=entries,
                                                 version=version,
                                                 encoding=encoding,
                                                 language=language,
                                                 status_code=status_code,
                                                 updated=updated)
                        await scan(self, jid_bare, db_file, url)
                        old = Config.get_setting_value(self.settings, jid_bare, 'old')
                        feed_id = sqlite.get_feed_id(db_file, url)
                        feed_id = feed_id[0]
                        if not old:
                            await sqlite.mark_feed_as_read(db_file, feed_id)
                        result_final = {'link' : url,
                                        'index' : feed_id,
                                        'name' : title,
                                        'code' : status_code,
                                        'error' : False,
                                        'message': message,
                                        'exist' : False,
                                        'node' : None}
                        break
                    # NOTE This elif statement be unnecessary
                    # when feedparser be supporting json feed.
                    elif is_feed_json(document):
                        feed = json.loads(document)
                        if "title" in feed.keys():
                            title = feed["title"]
                        else:
                            title = urlsplit(url).netloc
                        if "language" in feed.keys():
                            language = feed["language"]
                        else:
                            language = ''
                        if "encoding" in feed.keys():
                            encoding = feed["encoding"]
                        else:
                            encoding = ''
                        if "date_published" in feed.keys():
                            updated = feed["date_published"]
                            try:
                                updated = dt.convert_struct_time_to_iso8601(updated)
                            except:
                                updated = ''
                        else:
                            updated = ''
                        version = 'json' + feed["version"].split('/').pop()
                        entries = len(feed["items"])
                        await sqlite.insert_feed(db_file, url, title, node,
                                                 entries=entries,
                                                 version=version,
                                                 encoding=encoding,
                                                 language=language,
                                                 status_code=status_code,
                                                 updated=updated)
                        await scan_json(self, jid_bare, db_file, url)
                        old = Config.get_setting_value(self.settings, jid_bare, 'old')
                        if not old:
                            feed_id = sqlite.get_feed_id(db_file, url)
                            feed_id = feed_id[0]
                            await sqlite.mark_feed_as_read(db_file, feed_id)
                        result_final = {'link' : url,
                                        'index' : feed_id,
                                        'name' : title,
                                        'code' : status_code,
                                        'error' : False,
                                        'message': message,
                                        'exist' : False,
                                        'node' : None}
                        break
                    else:
                        # NOTE Do not be tempted to return a compact dictionary.
                        #      That is, dictionary within dictionary
                        #      Return multiple dictionaries in a list or tuple.
                        result = await crawl.probe_page(url, document)
                        if not result:
                            # Get out of the loop with dict indicating error.
                            result_final = {'link' : url,
                                            'index' : None,
                                            'name' : None,
                                            'code' : status_code,
                                            'error' : True,
                                            'message': message,
                                            'exist' : False,
                                            'node' : None}
                            break
                        elif isinstance(result, list):
                            # Get out of the loop and deliver a list of dicts.
                            result_final = result
                            break
                        else:
                            # Go back up to the while loop and try again.
                            url = result['link']
                else:
                    result_final = {'link' : url,
                                    'index' : None,
                                    'name' : None,
                                    'code' : status_code,
                                    'error' : True,
                                    'message': message,
                                    'exist' : False,
                                    'node' : None}
                    break
            else:
                ix = exist_node[1]
                node = exist_node[2]
                message = 'Node is already allocated.'
                result_final = {'link' : url,
                                'index' : ix,
                                'name' : None,
                                'code' : None,
                                'error' : False,
                                'message': message,
                                'exist' : False,
                                'node' : node}
                break
        else:
            ix = exist_feed[0]
            name = exist_feed[1]
            message = 'URL already exist.'
            result_final = {'link' : url,
                            'index' : ix,
                            'name' : name,
                            'code' : None,
                            'error' : False,
                            'message': message,
                            'exist' : True,
                            'node' : None}
            break
    return result_final


async def scan_json(self, jid_bare, db_file, url):
    """
    Check feeds for new entries.

    Parameters
    ----------
    db_file : str
        Path to database file.
    url : str, optional
        URL. The default is None.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} url: {}'
                .format(function_name, db_file, url))
    if isinstance(url, tuple): url = url[0]
    result = await fetch.http(url)
    if not result['error']:
        document = result['content']
        status = result['status_code']
        new_entries = []
        if document and status == 200:
            feed = json.loads(document)
            entries = feed["items"]
            await remove_nonexistent_entries_json(self, jid_bare, db_file, url, feed)
            try:
                feed_id = sqlite.get_feed_id(db_file, url)
                feed_id = feed_id[0]
                # await sqlite.update_feed_validity(
                #     db_file, feed_id, valid)
                if "date_published" in feed.keys():
                    updated = feed["date_published"]
                    try:
                        updated = dt.convert_struct_time_to_iso8601(updated)
                    except:
                        updated = ''
                else:
                    updated = ''
                feed_id = sqlite.get_feed_id(db_file, url)
                feed_id = feed_id[0]
                await sqlite.update_feed_properties(
                    db_file, feed_id, len(feed["items"]), updated)
                # await update_feed_status
            except (
                    IncompleteReadError,
                    IncompleteRead,
                    error.URLError
                    ) as e:
                logger.error(e)
                return
            # new_entry = 0
            for entry in entries:
                logger.debug('{}: entry: {}'
                            .format(function_name, entry["title"]))
                if "date_published" in entry.keys():
                    date = entry["date_published"]
                    date = dt.rfc2822_to_iso8601(date)
                elif "date_modified" in entry.keys():
                    date = entry["date_modified"]
                    date = dt.rfc2822_to_iso8601(date)
                else:
                    date = dt.now()
                if "url" in entry.keys():
                    # link = complete_url(source, entry.link)
                    link = join_url(url, entry["url"])
                    link = trim_url(link)
                else:
                    link = url
                # title = feed["feed"]["title"]
                # title = "{}: *{}*".format(feed["feed"]["title"], entry.title)
                title = entry["title"] if "title" in entry.keys() else date
                entry_id = entry["id"] if "id" in entry.keys() else link
                feed_id = sqlite.get_feed_id(db_file, url)
                feed_id = feed_id[0]
                exist = sqlite.check_entry_exist(db_file, feed_id,
                                                 entry_id=entry_id,
                                                 title=title, link=link,
                                                 date=date)
                if not exist:
                    summary = entry["summary"] if "summary" in entry.keys() else ''
                    if not summary:
                        summary = (entry["content_html"]
                                   if "content_html" in entry.keys()
                                   else '')
                    if not summary:
                        summary = (entry["content_text"]
                                   if "content_text" in entry.keys()
                                   else '')
                    read_status = 0
                    pathname = urlsplit(link).path
                    string = (
                        "{} {} {}"
                        ).format(
                            title, summary, pathname)
                    if self.settings['default']['filter']:
                        print('Filter is now processing data.')
                        allow_list = config.is_include_keyword(db_file,
                                                               "allow", string)
                        if not allow_list:
                            reject_list = config.is_include_keyword(db_file,
                                                                    "deny",
                                                                    string)
                            if reject_list:
                                read_status = 1
                                logger.debug('Rejected : {}'
                                             '\n'
                                             'Keyword  : {}'
                                             .format(link, reject_list))
                    if isinstance(date, int):
                        logger.error('Variable "date" is int: {}'.format(date))
                    media_link = ''
                    if "attachments" in entry.keys():
                        for e_link in entry["attachments"]:
                            try:
                                # if (link.rel == "enclosure" and
                                #     (link.type.startswith("audio/") or
                                #      link.type.startswith("image/") or
                                #      link.type.startswith("video/"))
                                #     ):
                                media_type = e_link["mime_type"][:e_link["mime_type"].index("/")]
                                if media_type in ("audio", "image", "video"):
                                    media_link = e_link["url"]
                                    media_link = join_url(url, e_link["url"])
                                    media_link = trim_url(media_link)
                                    break
                            except:
                                logger.error('KeyError: "url"\n'
                                             'Missing "url" attribute for {}'
                                             .format(url))
                                logger.error('Continue scanning for next '
                                             'potential enclosure of {}'
                                             .format(link))
                    entry = {
                        "title": title,
                        "link": link,
                        "enclosure": media_link,
                        "entry_id": entry_id,
                        "date": date,
                        "read_status": read_status
                        }
                    new_entries.extend([entry])
                    # await sqlite.add_entry(
                    #     db_file, title, link, entry_id,
                    #     url, date, read_status)
                    # await sqlite.set_date(db_file, url)
        if len(new_entries):
            feed_id = sqlite.get_feed_id(db_file, url)
            feed_id = feed_id[0]
            await sqlite.add_entries_and_update_timestamp(db_file, feed_id,
                                                          new_entries)


def view_feed(url, feed):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: url: {}'
                 .format(function_name, url))
    if "title" in feed["feed"].keys():
        title = feed["feed"]["title"]
    else:
        title = urlsplit(url).netloc
    entries = feed.entries
    response = "Preview of {}:\n\n```\n".format(title)
    counter = 0
    for entry in entries:
        counter += 1
        if entry.has_key("title"):
            title = entry.title
        else:
            title = "*** No title ***"
        if entry.has_key("link"):
            # link = complete_url(source, entry.link)
            link = join_url(url, entry.link)
            link = trim_url(link)
        else:
            link = "*** No link ***"
        if entry.has_key("published"):
            date = entry.published
            date = dt.rfc2822_to_iso8601(date)
        elif entry.has_key("updated"):
            date = entry.updated
            date = dt.rfc2822_to_iso8601(date)
        else:
            date = "*** No date ***"
        response += ("Title : {}\n"
                     "Date  : {}\n"
                     "Link  : {}\n"
                     "Count : {}\n"
                     "\n"
                     .format(title, date, link, counter))
        if counter > 4:
            break
    response += (
        "```\nSource: {}"
        ).format(url)
    return response


def view_entry(url, feed, num):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: url: {} num: {}'
                .format(function_name, url, num))
    if "title" in feed["feed"].keys():
        title = feed["feed"]["title"]
    else:
        title = urlsplit(url).netloc
    entries = feed.entries
    num = int(num) - 1
    entry = entries[num]
    response = "Preview of {}:\n\n```\n".format(title)
    if entry.has_key("title"):
        title = entry.title
    else:
        title = "*** No title ***"
    if entry.has_key("published"):
        date = entry.published
        date = dt.rfc2822_to_iso8601(date)
    elif entry.has_key("updated"):
        date = entry.updated
        date = dt.rfc2822_to_iso8601(date)
    else:
        date = "*** No date ***"
    if entry.has_key("summary"):
        summary = entry.summary
        # Remove HTML tags
        summary = BeautifulSoup(summary, "lxml").text
        # TODO Limit text length
        summary = summary.replace("\n\n\n", "\n\n")
    else:
        summary = "*** No summary ***"
    if entry.has_key("link"):
        # link = complete_url(source, entry.link)
        link = join_url(url, entry.link)
        link = trim_url(link)
    else:
        link = "*** No link ***"
    response = ("{}\n"
                "\n"
                # "> {}\n"
                "{}\n"
                "\n"
                "{}\n"
                "\n"
                .format(title, summary, link))
    return response


# TODO get all active feeds of active accounts and scan the feed with the earliest scanned time
# TODO Rename function name (idea: scan_and_populate)
async def scan(self, jid_bare, db_file, url):
    """
    Check feeds for new entries.

    Parameters
    ----------
    db_file : str
        Path to database file.
    url : str, optional
        URL. The default is None.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} url: {}'
                .format(function_name, db_file, url))
    if isinstance(url, tuple): url = url[0]
    result = await fetch.http(url)
    feed_id = sqlite.get_feed_id(db_file, url)
    feed_id = feed_id[0]
    status_code = result['status_code']
    await sqlite.update_feed_status(db_file, feed_id, status_code)
    if not result['error']:
        document = result['content']
        status = result['status_code']
        new_entries = []
        if document and status == 200:
            feed = parse(document)
            entries = feed.entries
            # length = len(entries)
            await remove_nonexistent_entries(self, jid_bare, db_file, url, feed)
            try:
                if feed.bozo:
                    # bozo = (
                    #     "WARNING: Bozo detected for feed: {}\n"
                    #     "For more information, visit "
                    #     "https://pythonhosted.org/feedparser/bozo.html"
                    #     ).format(url)
                    # print(bozo)
                    valid = 0
                else:
                    valid = 1
                feed_id = sqlite.get_feed_id(db_file, url)
                feed_id = feed_id[0]
                await sqlite.update_feed_validity(
                    db_file, feed_id, valid)
                if "updated_parsed" in feed["feed"].keys():
                    updated = feed["feed"]["updated_parsed"]
                    try:
                        updated = dt.convert_struct_time_to_iso8601(updated)
                    except:
                        updated = ''
                else:
                    updated = ''
                feed_id = sqlite.get_feed_id(db_file, url)
                feed_id = feed_id[0]
                await sqlite.update_feed_properties(db_file, feed_id,
                                                    len(feed["entries"]), updated)
                # await update_feed_status
            except (IncompleteReadError, IncompleteRead, error.URLError) as e:
                logger.error(e)
                return
            # new_entry = 0
            for entry in entries:
                logger.debug('{}: entry: {}'.format(function_name, entry.link))
                if entry.has_key("published"):
                    date = entry.published
                    date = dt.rfc2822_to_iso8601(date)
                elif entry.has_key("updated"):
                    date = entry.updated
                    date = dt.rfc2822_to_iso8601(date)
                else:
                    date = dt.now()
                if entry.has_key("link"):
                    # link = complete_url(source, entry.link)
                    link = join_url(url, entry.link)
                    link = trim_url(link)
                else:
                    link = url
                # title = feed["feed"]["title"]
                # title = "{}: *{}*".format(feed["feed"]["title"], entry.title)
                title = entry.title if entry.has_key("title") else date
                entry_id = entry.id if entry.has_key("id") else link
                feed_id = sqlite.get_feed_id(db_file, url)
                feed_id = feed_id[0]
                exist = sqlite.check_entry_exist(db_file, feed_id,
                                                 entry_id=entry_id,
                                                 title=title, link=link,
                                                 date=date)
                if not exist:
                    summary = entry.summary if entry.has_key("summary") else ''
                    read_status = 0
                    pathname = urlsplit(link).path
                    string = (
                        "{} {} {}"
                        ).format(
                            title, summary, pathname)
                    if self.settings['default']['filter']:
                        print('Filter is now processing data.')
                        allow_list = config.is_include_keyword(db_file,
                                                               "allow", string)
                        if not allow_list:
                            reject_list = config.is_include_keyword(db_file,
                                                                    "deny",
                                                                    string)
                            if reject_list:
                                read_status = 1
                                logger.debug('Rejected : {}'
                                             '\n'
                                             'Keyword  : {}'
                                             .format(link, reject_list))
                    if isinstance(date, int):
                        logger.error('Variable "date" is int: {}'.format(date))
                    media_link = ''
                    if entry.has_key("links"):
                        for e_link in entry.links:
                            try:
                                # if (link.rel == "enclosure" and
                                #     (link.type.startswith("audio/") or
                                #      link.type.startswith("image/") or
                                #      link.type.startswith("video/"))
                                #     ):
                                media_type = e_link.type[:e_link.type.index("/")]
                                if e_link.has_key("rel"):
                                    if (e_link.rel == "enclosure" and
                                        media_type in ("audio", "image", "video")):
                                        media_link = e_link.href
                                        media_link = join_url(url, e_link.href)
                                        media_link = trim_url(media_link)
                                        break
                            except:
                                logger.error('KeyError: "href"\n'
                                             'Missing "href" attribute for {}'
                                             .format(url))
                                logger.error('Continue scanning for next '
                                             'potential enclosure of {}'
                                             .format(link))
                    entry = {
                        "title": title,
                        "link": link,
                        "summary": summary,
                        "enclosure": media_link,
                        "entry_id": entry_id,
                        "date": date,
                        "read_status": read_status
                        }
                    new_entries.extend([entry])
                    # await sqlite.add_entry(
                    #     db_file, title, link, entry_id,
                    #     url, date, read_status)
                    # await sqlite.set_date(db_file, url)
        if len(new_entries):
            feed_id = sqlite.get_feed_id(db_file, url)
            feed_id = feed_id[0]
            await sqlite.add_entries_and_update_timestamp(db_file, feed_id,
                                                          new_entries)


def get_document_title(data):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}'.format(function_name))
    try:
        document = Document(data)
        title = document.short_title()
    except:
        document = BeautifulSoup(data, 'html.parser')
        title = document.title.string
    return title


def get_document_content(data):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}'.format(function_name))
    try:
        document = Document(data)
        content = document.summary()
    except:
        document = BeautifulSoup(data, 'html.parser')
        content = data
    return content


def get_document_content_as_text(data):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}'.format(function_name))
    try:
        document = Document(data)
        content = document.summary()
    except:
        document = BeautifulSoup(data, 'html.parser')
        content = data
    text = remove_html_tags(content)
    return text


def generate_document(data, url, ext, filename, readability=False):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: url: {} ext: {} filename: {}'
                .format(function_name, url, ext, filename))
    error = None
    if readability:
        try:
            document = Document(data)
            content = document.summary()
        except:
            content = data
            logger.warning('Check that package readability is installed.')
    else:
        content = data
    match ext:
        case "epub":
            filename = filename.split('.')
            filename.pop()
            filename = '.'.join(filename)
            error = generate_epub(content, filename)
            if error:
                logger.error(error)
                # logger.error(
                #     "Check that packages xml2epub is installed, "
                #     "or try again.")
        case "html":
            generate_html(content, filename)
        case "md":
            try:
                generate_markdown(content, filename)
            except:
                logger.warning('Check that package html2text '
                                'is installed, or try again.')
                error = 'Package html2text was not found.'
        case "pdf":
            error = generate_pdf(content, filename)
            if error:
                logger.error(error)
                # logger.warning(
                #     "Check that packages pdfkit and wkhtmltopdf "
                #     "are installed, or try again.")
                # error = (
                #     "Package pdfkit or wkhtmltopdf was not found.")
        case "txt":
            generate_txt(content, filename)
    if error:
        return error

    # TODO Either adapt it to filename
    # or change it to something else
    #filename = document.title()
    # with open(filename, 'w') as file:
    #     html_doc = document.summary()
    #     file.write(html_doc)


async def extract_image_from_feed(db_file, feed_id, url):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} feed_id: {} url: {}'
                .format(function_name, db_file, feed_id, url))
    feed_url = sqlite.get_feed_url(db_file, feed_id)
    feed_url = feed_url[0]
    result = await fetch.http(feed_url)
    if not result['error']:
        document = result['content']
        feed = parse(document)
        for entry in feed.entries:
            try:
                if entry.link == url:
                    for link in entry.links:
                        if (link.rel == "enclosure" and
                            link.type.startswith("image/")):
                            image_url = link.href
                            return image_url
            except:
                logger.error(url)
                logger.error('AttributeError: object has no attribute "link"')


async def extract_image_from_html(url):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: url: {}'.format(function_name, url))
    result = await fetch.http(url)
    if not result['error']:
        data = result['content']
        try:
            document = Document(data)
            content = document.summary()
        except:
            content = data
            logger.warning('Check that package readability is installed.')
        tree = html.fromstring(content)
        # TODO Exclude banners, class="share" links etc.
        images = tree.xpath(
            '//img[not('
                'contains(@src, "avatar") or '
                'contains(@src, "emoji") or '
                'contains(@src, "icon") or '
                'contains(@src, "logo") or '
                'contains(@src, "letture") or '
                'contains(@src, "search") or '
                'contains(@src, "share") or '
                'contains(@src, "smiley")'
            ')]/@src')
        if len(images):
            image = images[0]
            image = str(image)
            image_url = complete_url(url, image)
            return image_url


def generate_epub(text, filename):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: text: {} pathname: {}'.format(function_name, text, filename))
    ## create an empty eBook
    filename_list = filename.split("/")
    file_title = filename_list.pop()
    directory = "/".join(filename_list)
    book = xml2epub.Epub(file_title)
    ## create chapters by url
    # chapter0 = xml2epub.create_chapter_from_string(text, title=filename, strict=False)
    chapter0 = xml2epub.create_chapter_from_string(text, strict=False)
    #### create chapter objects
    # chapter1 = xml2epub.create_chapter_from_url("https://dev.to/devteam/top-7-featured-dev-posts-from-the-past-week-h6h")
    # chapter2 = xml2epub.create_chapter_from_url("https://dev.to/ks1912/getting-started-with-docker-34g6")
    ## add chapters to your eBook
    try:
        book.add_chapter(chapter0)
        # book.add_chapter(chapter1)
        # book.add_chapter(chapter2)
        ## generate epub file
        book.create_epub(directory, absolute_location=filename)
    except ValueError as error:
        return error
        


def generate_html(text, filename):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: text: {} filename: {}'.format(function_name, text, filename))
    with open(filename, 'w') as file:
        file.write(text)


def generate_markdown(text, filename):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: text: {} filename: {}'.format(function_name, text, filename))
    h2m = html2text.HTML2Text()
    # Convert HTML to Markdown
    markdown = h2m.handle(text)
    with open(filename, 'w') as file:
        file.write(markdown)


def generate_pdf(text, filename):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: text: {} filename: {}'.format(function_name, text, filename))
    try:
        pdfkit.from_string(text, filename)
    except IOError as error:
        return error
    except OSError as error:
        return error


def generate_txt(text, filename):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: text: {} filename: {}'.format(function_name, text, filename))
    text = remove_html_tags(text)
    with open(filename, 'w') as file:
        file.write(text)

def remove_html_tags(data):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}'.format(function_name))
    data = BeautifulSoup(data, "lxml").text
    data = data.replace("\n\n", "\n")
    return data

# TODO Add support for eDonkey, Gnutella, Soulseek
async def get_magnet(link):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: {}'.format(function_name, link))
    parted_link = urlsplit(link)
    queries = parse_qs(parted_link.query)
    query_xt = queries["xt"][0]
    if query_xt.startswith("urn:btih:"):
        filename = queries["dn"][0]
        checksum = query_xt[len("urn:btih:"):]
        torrent = await fetch.magnet(link)
        logger.debug('Attempting to retrieve {} ({})'
                     .format(filename, checksum))
        if not torrent:
            logger.debug('Attempting to retrieve {} from HTTP caching service'
                         .format(filename))
            urls = [
                'https://watercache.libertycorp.org/get/{}/{}',
                'https://itorrents.org/torrent/{}.torrent?title={}',
                'https://firecache.libertycorp.org/get/{}/{}',
                'http://fcache63sakpihd44kxdduy6kgpdhgejgp323wci435zwy6kiylcnfad.onion/get/{}/{}'
                ]
            for url in urls:
                torrent = fetch.http(url.format(checksum, filename))
                if torrent:
                    break
    return torrent


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
    for item in items:
        ix = item[0]
        entry_title = item[1]
        entry_link = item[2]
        entry_id = item[3]
        timestamp = item[4]
        read_status = item[5]
        valid = False
        for entry in entries:
            title = None
            link = None
            time = None
            # valid = False
            # TODO better check and don't repeat code
            if entry.has_key("id") and entry_id:
                if entry.id == entry_id:
                    # print("compare1:", entry.id)
                    # print("compare2:", entry_id)
                    # print("============")
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
                    # print("compare11:", title, link, time)
                    # print("compare22:", entry_title, entry_link, timestamp)
                    # print("============")
                    time = dt.rfc2822_to_iso8601(entry.published)
                    if (entry_title == title and
                        entry_link == link and
                        timestamp == time):
                        valid = True
                        break
                else:
                    if (entry_title == title and
                        entry_link == link):
                        # print("compare111:", title, link)
                        # print("compare222:", entry_title, entry_link)
                        # print("============")
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



async def remove_nonexistent_entries_json(self, jid_bare, db_file, url, feed):
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
    logger.debug('{}: db_file: {}: url: {}'
                .format(function_name, db_file, url))
    feed_id = sqlite.get_feed_id(db_file, url)
    feed_id = feed_id[0]
    items = sqlite.get_entries_of_feed(db_file, feed_id)
    entries = feed["items"]
    limit = Config.get_setting_value(self.settings, jid_bare, 'archive')
    for item in items:
        ix = item[0]
        entry_title = item[1]
        entry_link = item[2]
        entry_id = item[3]
        timestamp = item[4]
        read_status = item[5]
        valid = False
        for entry in entries:
            title = None
            link = None
            time = None
            # valid = False
            # TODO better check and don't repeat code
            if entry.has_key("id") and entry_id:
                if entry["id"] == entry_id:
                    # print("compare1:", entry.id)
                    # print("compare2:", entry_id)
                    # print("============")
                    valid = True
                    break
            else:
                if entry.has_key("title"):
                    title = entry["title"]
                else:
                    title = feed["title"]
                if entry.has_key("link"):
                    link = join_url(url, entry["link"])
                else:
                    link = url
                # "date_published" "date_modified"
                if entry.has_key("date_published") and timestamp:
                    time = dt.rfc2822_to_iso8601(entry["date_published"])
                    if (entry_title == title and
                        entry_link == link and
                        timestamp == time):
                        valid = True
                        break
                else:
                    if (entry_title == title and
                        entry_link == link):
                        valid = True
                        break
        if not valid:
            print("CHECK ENTRY OF JSON FEED IN ARCHIVE")
            if read_status == 1:
                await sqlite.delete_entry_by_id(db_file, ix)
            else:
                await sqlite.archive_entry(db_file, ix)
        await sqlite.maintain_archive(db_file, limit)
