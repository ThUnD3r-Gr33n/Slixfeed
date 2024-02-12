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

import asyncio
from asyncio.exceptions import IncompleteReadError
from bs4 import BeautifulSoup
from feedparser import parse
from http.client import IncompleteRead
import json
import logging
from lxml import html
import os
import slixfeed.config as config
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
from slixfeed.xmpp.message import XmppMessage
from slixfeed.xmpp.presence import XmppPresence
from slixfeed.xmpp.upload import XmppUpload
from slixfeed.xmpp.utility import get_chat_type
import tomllib
from urllib import error
from urllib.parse import parse_qs, urlsplit
import xml.etree.ElementTree as ET

try:
    import xml2epub
except ImportError:
    logging.info(
        "Package xml2epub was not found.\n"
        "ePUB support is disabled.")

try:
    import html2text
except ImportError:
    logging.info(
        "Package html2text was not found.\n"
        "Markdown support is disabled.")

try:
    import pdfkit
except ImportError:
    logging.info(
        "Package pdfkit was not found.\n"
        "PDF support is disabled.")

try:
    from readability import Document
except ImportError:
    logging.info(
        "Package readability was not found.\n"
        "Arc90 Lab algorithm is disabled.")


async def xmpp_send_status(self, jid):
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
    db_file = config.get_pathname_to_database(jid_file)
    enabled = config.get_setting_value(db_file, 'enabled')
    if not enabled:
        status_mode = 'xa'
        status_text = '📪️ Send "Start" to receive updates'
    else:
        feeds = await sqlite.get_number_of_items(db_file, 'feeds')
        # print(await current_time(), jid, "has", feeds, "feeds")
        if not feeds:
            status_mode = 'available'
            status_text = '📪️ Send a URL from a blog or a news website'
        else:
            unread = await sqlite.get_number_of_entries_unread(db_file)
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


async def xmpp_send_update(self, jid, num=None):
    """
    Send news items as messages.

    Parameters
    ----------
    jid : str
        Jabber ID.
    num : str, optional
        Number. The default is None.
    """
    jid_file = jid.replace('/', '_')
    db_file = config.get_pathname_to_database(jid_file)
    enabled = config.get_setting_value(db_file, 'enabled')
    if enabled:
        show_media = config.get_setting_value(db_file, 'media')
        if not num:
            num = config.get_setting_value(db_file, 'quantum')
        else:
            num = int(num)
        results = await sqlite.get_unread_entries(db_file, num)
        news_digest = ''
        media = None
        chat_type = await get_chat_type(self, jid)
        for result in results:
            ix = result[0]
            title_e = result[1]
            url = result[2]
            enclosure = result[3]
            feed_id = result[4]
            date = result[5]
            title_f = sqlite.get_feed_title(db_file, feed_id)
            title_f = title_f[0]
            news_digest += list_unread_entries(result, title_f)
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

        # await start_tasks_xmpp(self, jid, ['status'])
        # await refresh_task(self, jid, send_update, 'interval')

    # interval = await initdb(
    #     jid,
    #     sqlite.get_settings_value,
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
    config_dir = config.get_default_config_directory()
    with open(config_dir + '/' + filename, mode="rb") as commands:
        cmds = tomllib.load(commands)
    if command and section:
        try:
            cmd_list = cmds[section][command]
        except KeyError as e:
            logging.error(str(e))
            cmd_list = None
    elif section:
        try:
            cmd_list = []
            for cmd in cmds[section]:
                cmd_list.extend([cmd])
        except KeyError as e:
            logging.error('KeyError:' + str(e))
            cmd_list = None
    else:
        cmd_list = []
        for cmd in cmds:
            cmd_list.extend([cmd])
    return cmd_list


async def xmpp_change_interval(self, key, val, jid, jid_file, message=None):
    if val:
        # response = (
        #     'Updates will be sent every {} minutes.'
        #     ).format(response)
        db_file = config.get_pathname_to_database(jid_file)
        if sqlite.get_settings_value(db_file, key):
            await sqlite.update_settings_value(db_file, [key, val])
        else:
            await sqlite.set_settings_value(db_file, [key, val])
        # NOTE Perhaps this should be replaced
        # by functions clean and start
        await task.refresh_task(self, jid, task.task_send, key, val)
        response = ('Updates will be sent every {} minutes.'
                    .format(val))
    else:
        response = 'Missing value.'
    if message:
        XmppMessage.send_reply(self, message, response)


async def reset_settings(jid_file):
    db_file = config.get_pathname_to_database(jid_file)
    await sqlite.delete_settings(db_file)
    response = 'Default settings have been restored.'
    return response

async def xmpp_start_updates(self, message, jid, jid_file):
    key = 'enabled'
    val = 1
    db_file = config.get_pathname_to_database(jid_file)
    if sqlite.get_settings_value(db_file, key):
        await sqlite.update_settings_value(db_file, [key, val])
    else:
        await sqlite.set_settings_value(db_file, [key, val])
    status_type = 'available'
    status_message = '📫️ Welcome back!'
    XmppPresence.send(self, jid, status_message, status_type=status_type)
    message_body = 'Updates are enabled.'
    XmppMessage.send_reply(self, message, message_body)
    await asyncio.sleep(5)
    await task.start_tasks_xmpp(self, jid, ['check', 'status', 'interval'])


async def xmpp_stop_updates(self, message, jid, jid_file):
    key = 'enabled'
    val = 0
    db_file = config.get_pathname_to_database(jid_file)
    if sqlite.get_settings_value(db_file, key):
        await sqlite.update_settings_value(db_file, [key, val])
    else:
        await sqlite.set_settings_value(db_file, [key, val])
    task.clean_tasks_xmpp(self, jid, ['interval', 'status'])
    message_body = 'Updates are disabled.'
    XmppMessage.send_reply(self, message, message_body)
    status_type = 'xa'
    status_message = '📪️ Send "Start" to receive Jabber updates'
    XmppPresence.send(self, jid, status_message, status_type=status_type)


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


def list_unread_entries(result, feed_title):
    # TODO Add filtering
    # TODO Do this when entry is added to list and mark it as read
    # DONE!
    # results = []
    # if get_settings_value(db_file, "filter-deny"):
    #     while len(results) < num:
    #         result = cur.execute(sql).fetchone()
    #         blacklist = await get_settings_value(db_file, "filter-deny").split(",")
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
    ix = result[0]
    title = result[1]
    # # TODO Retrieve summary from feed
    # # See fetch.view_entry
    # summary = result[2]
    # # Remove HTML tags
    # try:
    #     summary = BeautifulSoup(summary, "lxml").text
    # except:
    #     print(result[2])
    #     breakpoint()
    # # TODO Limit text length
    # summary = summary.replace("\n\n\n", "\n\n")
    # length = await get_settings_value(db_file, "length")
    # summary = summary[:length] + " […]"
    # summary = summary.strip().split('\n')
    # summary = ["> " + line for line in summary]
    # summary = "\n".join(summary)
    link = result[2]
    link = remove_tracking_parameters(link)
    link = (replace_hostname(link, "link")) or link
    news_item = (
        "\n{}\n{}\n{} [{}]\n"
        ).format(
            str(title), str(link), str(feed_title), str(ix)
            )
    return news_item


def list_search_results(query, results):
    message = (
        "Search results for '{}':\n\n```"
        ).format(query)
    for result in results:
        message += (
            "\n{}\n{}\n"
            ).format(str(result[0]), str(result[1]))
    if len(results):
        message += "```\nTotal of {} results".format(len(results))
    else:
        message = "No results were found for: {}".format(query)
    return message


def list_feeds_by_query(db_file, query):
    results = sqlite.search_feeds(db_file, query)
    message = (
        'Feeds containing "{}":\n\n```'
        .format(query))
    for result in results:
        message += (
            '\nName : {} [{}]'
            '\nURL  : {}'
            '\n'
            .format(str(result[0]), str(result[1]), str(result[2])))
    if len(results):
        message += "\n```\nTotal of {} feeds".format(len(results))
    else:
        message = "No feeds were found for: {}".format(query)
    return message


async def list_statistics(db_file):
    """
    Return table statistics.

    Parameters
    ----------
    db_file : str
        Path to database file.

    Returns
    -------
    msg : str
        Statistics as message.
    """
    entries_unread = await sqlite.get_number_of_entries_unread(db_file)
    entries = await sqlite.get_number_of_items(db_file, 'entries')
    archive = await sqlite.get_number_of_items(db_file, 'archive')
    entries_all = entries + archive
    feeds_active = await sqlite.get_number_of_feeds_active(db_file)
    feeds_all = await sqlite.get_number_of_items(db_file, 'feeds')
    key_archive = config.get_setting_value(db_file, 'archive')
    key_interval = config.get_setting_value(db_file, 'interval')
    key_quantum = config.get_setting_value(db_file, 'quantum')
    key_enabled = config.get_setting_value(db_file, 'enabled')

    # msg = """You have {} unread news items out of {} from {} news sources.
    #       """.format(unread_entries, entries, feeds)

    # try:
    #     value = cur.execute(sql, par).fetchone()[0]
    # except:
    #     print("Error for key:", key)
    #     value = "Default"
    # values.extend([value])

    message = ("```"
               "\nSTATISTICS\n"
               "News items   : {}/{}\n"
               "News sources : {}/{}\n"
               "\nOPTIONS\n"
               "Items to archive : {}\n"
               "Update interval  : {}\n"
               "Items per update : {}\n"
               "Operation status : {}\n"
               "```").format(entries_unread,
                             entries_all,
                             feeds_active,
                             feeds_all,
                             key_archive,
                             key_interval,
                             key_quantum,
                             key_enabled)
    return message


# FIXME Replace counter by len
def list_last_entries(results, num):
    message = "Recent {} titles:\n\n```".format(num)
    for result in results:
        message += ("\n{}\n{}\n"
                    .format(str(result[0]), str(result[1])))
    if len(results):
        message += "```\n"
    else:
        message = "There are no news at the moment."
    return message


def list_feeds(results):
    message = "\nList of subscriptions:\n\n```\n"
    for result in results:
        message += ("Name : {}\n"
                    "URL  : {}\n"
                    # "Updated : {}\n"
                    # "Status  : {}\n"
                    "ID   : {}\n"
                    "\n"
                    .format(str(result[0]), str(result[1]), str(result[2])))
    if len(results):
        message += ('```\nTotal of {} subscriptions.\n'
                    .format(len(results)))
    else:
        message = ('List of subscriptions is empty.\n'
                   'To add feed, send a URL\n'
                   'Featured feed: '
                   'https://reclaimthenet.org/feed/')
    return message


async def list_bookmarks(self):
    conferences = await XmppBookmark.get(self)
    message = '\nList of groupchats:\n\n```\n'
    for conference in conferences:
        message += ('{}\n'
                    '\n'
                    .format(conference['jid']))
    message += ('```\nTotal of {} groupchats.\n'
                .format(len(conferences)))
    return message


def export_to_markdown(jid, filename, results):
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


async def import_opml(db_file, url):
    result = await fetch.http(url)
    document = result[0]
    if document:
        root = ET.fromstring(document)
        before = await sqlite.get_number_of_items(
            db_file, 'feeds')
        feeds = []
        for child in root.findall(".//outline"):
            url = child.get("xmlUrl")
            title = child.get("text")
            # feed = (url, title)
            # feeds.extend([feed])
            feeds.extend([(url, title)])
        await sqlite.import_feeds(db_file, feeds)
        await sqlite.add_metadata(db_file)
        after = await sqlite.get_number_of_items(
            db_file, 'feeds')
        difference = int(after) - int(before)
        return difference


async def add_feed(db_file, url):
    while True:
        exist = await sqlite.get_feed_id_and_name(db_file, url)
        if not exist:
            result = await fetch.http(url)
            document = result[0]
            status_code = result[1]
            if document:
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
                    await sqlite.insert_feed(
                        db_file, url,
                        title=title,
                        entries=entries,
                        version=version,
                        encoding=encoding,
                        language=language,
                        status_code=status_code,
                        updated=updated
                        )
                    await scan(db_file, url)
                    old = config.get_setting_value(db_file, "old")
                    if not old:
                        feed_id = await sqlite.get_feed_id(db_file, url)
                        feed_id = feed_id[0]
                        await sqlite.mark_feed_as_read(db_file, feed_id)
                    response = ('> {}\nNews source "{}" has been '
                                'added to subscription list.'
                                .format(url, title))
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
                    await sqlite.insert_feed(
                        db_file, url,
                        title=title,
                        entries=entries,
                        version=version,
                        encoding=encoding,
                        language=language,
                        status_code=status_code,
                        updated=updated
                        )
                    await scan_json(
                        db_file, url)
                    old = config.get_setting_value(db_file, "old")
                    if not old:
                        feed_id = await sqlite.get_feed_id(db_file, url)
                        feed_id = feed_id[0]
                        await sqlite.mark_feed_as_read(db_file, feed_id)
                    response = ('> {}\nNews source "{}" has been '
                                'added to subscription list.'
                                .format(url, title))
                    break
                else:
                    result = await crawl.probe_page(
                        url, document)
                    if isinstance(result, str):
                        response = result
                        break
                    else:
                        url = result[0]
            else:
                response = ('> {}\nFailed to load URL.  Reason: {}'
                            .format(url, status_code))
                break
        else:
            ix = exist[0]
            name = exist[1]
            response = ('> {}\nNews source "{}" is already '
                        'listed in the subscription list at '
                        'index {}'.format(url, name, ix))
            break
    return response


async def scan_json(db_file, url):
    """
    Check feeds for new entries.

    Parameters
    ----------
    db_file : str
        Path to database file.
    url : str, optional
        URL. The default is None.
    """
    if isinstance(url, tuple): url = url[0]
    result = await fetch.http(url)
    try:
        document = result[0]
        status = result[1]
    except:
        return
    new_entries = []
    if document and status == 200:
        feed = json.loads(document)
        entries = feed["items"]
        await remove_nonexistent_entries_json(
            db_file, url, feed)
        try:
            feed_id = await sqlite.get_feed_id(db_file, url)
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
            feed_id = await sqlite.get_feed_id(db_file, url)
            feed_id = feed_id[0]
            await sqlite.update_feed_properties(
                db_file, feed_id, len(feed["items"]), updated)
            # await update_feed_status
        except (
                IncompleteReadError,
                IncompleteRead,
                error.URLError
                ) as e:
            logging.error(e)
            return
        # new_entry = 0
        for entry in entries:
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
            feed_id = await sqlite.get_feed_id(db_file, url)
            feed_id = feed_id[0]
            exist = await sqlite.check_entry_exist(
                db_file, feed_id, entry_id=entry_id,
                title=title, link=link, date=date)
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
                allow_list = await config.is_include_keyword(
                    db_file, "allow", string)
                if not allow_list:
                    reject_list = await config.is_include_keyword(
                        db_file, "deny", string)
                    if reject_list:
                        read_status = 1
                        logging.debug(
                            "Rejected : {}\n"
                            "Keyword  : {}".format(
                                link, reject_list))
                if isinstance(date, int):
                    logging.error(
                        "Variable 'date' is int: {}".format(date))
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
                            logging.info('KeyError: "url"\n'
                                          'Missing "url" attribute for {}'
                                          .format(url))
                            logging.info('Continue scanning for next '
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
        feed_id = await sqlite.get_feed_id(db_file, url)
        feed_id = feed_id[0]
        await sqlite.add_entries_and_update_timestamp(
            db_file, feed_id, new_entries)


async def view_feed(url):
    while True:
        result = await fetch.http(url)
        document = result[0]
        status = result[1]
        if document:
            feed = parse(document)
            # if is_feed(url, feed):
            if is_feed(feed):
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
                    response += (
                        "Title : {}\n"
                        "Date  : {}\n"
                        "Link  : {}\n"
                        "Count : {}\n"
                        "\n"
                        ).format(title, date, link, counter)
                    if counter > 4:
                        break
                response += (
                    "```\nSource: {}"
                    ).format(url)
                break
            else:
                result = await crawl.probe_page(
                    url, document)
                if isinstance(result, str):
                    response = result
                    break
                else:
                    url = result[0]
        else:
            response = ('> {}\nFailed to load URL.  Reason: {}'
                        .format(url, status))
            break
    return response


async def view_entry(url, num):
    while True:
        result = await fetch.http(url)
        document = result[0]
        status = result[1]
        if document:
            feed = parse(document)
            # if is_feed(url, feed):
            if is_feed(feed):
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
                response = (
                    "{}\n"
                    "\n"
                    # "> {}\n"
                    "{}\n"
                    "\n"
                    "{}\n"
                    "\n"
                    ).format(title, summary, link)
                break
            else:
                result = await crawl.probe_page(
                    url, document)
                if isinstance(result, str):
                    response = result
                    break
                else:
                    url = result[0]
        else:
            response = ('> {}\nFailed to load URL.  Reason: {}'
                        .format(url, status))
            break
    return response


async def scan(db_file, url):
    """
    Check feeds for new entries.

    Parameters
    ----------
    db_file : str
        Path to database file.
    url : str, optional
        URL. The default is None.
    """
    if isinstance(url, tuple): url = url[0]
    result = await fetch.http(url)
    try:
        document = result[0]
        status = result[1]
    except:
        return
    new_entries = []
    if document and status == 200:
        feed = parse(document)
        entries = feed.entries
        # length = len(entries)
        await remove_nonexistent_entries(
            db_file, url, feed)
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
            feed_id = await sqlite.get_feed_id(db_file, url)
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
            feed_id = await sqlite.get_feed_id(db_file, url)
            feed_id = feed_id[0]
            await sqlite.update_feed_properties(
                db_file, feed_id, len(feed["entries"]), updated)
            # await update_feed_status
        except (
                IncompleteReadError,
                IncompleteRead,
                error.URLError
                ) as e:
            logging.error(e)
            return
        # new_entry = 0
        for entry in entries:
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
            feed_id = await sqlite.get_feed_id(db_file, url)
            feed_id = feed_id[0]
            exist = await sqlite.check_entry_exist(
                db_file, feed_id, entry_id=entry_id,
                title=title, link=link, date=date)
            if not exist:
                summary = entry.summary if entry.has_key("summary") else ''
                read_status = 0
                pathname = urlsplit(link).path
                string = (
                    "{} {} {}"
                    ).format(
                        title, summary, pathname)
                allow_list = await config.is_include_keyword(
                    db_file, "allow", string)
                if not allow_list:
                    reject_list = await config.is_include_keyword(
                        db_file, "deny", string)
                    if reject_list:
                        read_status = 1
                        logging.debug(
                            "Rejected : {}\n"
                            "Keyword  : {}".format(
                                link, reject_list))
                if isinstance(date, int):
                    logging.error('Variable "date" is int: {}'
                                  .format(date))
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
                            logging.info('KeyError: "href"\n'
                                          'Missing "href" attribute for {}'
                                          .format(url))
                            logging.info('Continue scanning for next '
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
        feed_id = await sqlite.get_feed_id(db_file, url)
        feed_id = feed_id[0]
        await sqlite.add_entries_and_update_timestamp(
            db_file, feed_id, new_entries)


async def download_document(self, message, jid, jid_file, message_text, ix_url,
                            readability):
    ext = ' '.join(message_text.split(' ')[1:])
    ext = ext if ext else 'pdf'
    url = None
    error = None
    response = None
    if ext in ('epub', 'html', 'markdown', 'md', 'pdf', 'text', 'txt'):
        match ext:
            case 'markdown':
                ext = 'md'
            case 'text':
                ext = 'txt'
        status_type = 'dnd'
        status_message = ('📃️ Procesing request to produce {} document...'
                          .format(ext.upper()))
        XmppPresence.send(self, jid, status_message,
                               status_type=status_type)
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
                    title = get_document_title(data)
                    title = title.strip().lower()
                    for i in (' ', '-'):
                        title = title.replace(i, '_')
                    for i in ('?', '"', '\'', '!'):
                        title = title.replace(i, '')
                    filename = os.path.join(
                        cache_dir, 'readability',
                        title + '_' + dt.timestamp() + '.' + ext)
                    error = generate_document(data, url, ext, filename,
                                              readability)
                    if error:
                        response = ('> {}\n'
                                    'Failed to export {}.  Reason: {}'
                                    .format(url, ext.upper(), error))
                    else:
                        url = await XmppUpload.start(self, jid,
                                                 filename)
                        chat_type = await get_chat_type(self, jid)
                        XmppMessage.send_oob(self, jid, url, chat_type)
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
        XmppMessage.send_reply(self, message, response)


def get_document_title(data):
    try:
        document = Document(data)
        title = document.short_title()
    except:
        document = BeautifulSoup(data, 'html.parser')
        title = document.title.string
    return title


def generate_document(data, url, ext, filename, readability=False):
    error = None
    if readability:
        try:
            document = Document(data)
            content = document.summary()
        except:
            content = data
            logging.warning('Check that package readability is installed.')
    else:
        content = data
    match ext:
        case "epub":
            error = generate_epub(content, filename)
            if error:
                logging.error(error)
                # logging.error(
                #     "Check that packages xml2epub is installed, "
                #     "or try again.")
        case "html":
            generate_html(content, filename)
        case "md":
            try:
                generate_markdown(content, filename)
            except:
                logging.warning('Check that package html2text '
                                'is installed, or try again.')
                error = 'Package html2text was not found.'
        case "pdf":
            error = generate_pdf(content, filename)
            if error:
                logging.error(error)
                # logging.warning(
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
    feed_url = sqlite.get_feed_url(db_file, feed_id)
    feed_url = feed_url[0]
    result = await fetch.http(feed_url)
    document = result[0]
    if document:
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
                logging.error(url)
                logging.error('AttributeError: object has no attribute "link"')


async def extract_image_from_html(url):
    result = await fetch.http(url)
    data = result[0]
    if data:
        try:
            document = Document(data)
            content = document.summary()
        except:
            content = data
            logging.warning('Check that package readability is installed.')
        tree = html.fromstring(content)
        # TODO Exclude banners, class="share" links etc.
        images = tree.xpath(
            '//img[not('
                'contains(@src, "avatar") or '
                'contains(@src, "emoji") or '
                'contains(@src, "icon") or '
                'contains(@src, "logo") or '
                'contains(@src, "search") or '
                'contains(@src, "share") or '
                'contains(@src, "smiley")'
            ')]/@src')
        if len(images):
            image = images[0]
            image = str(image)
            image_url = complete_url(url, image)
            return image_url


def generate_epub(text, pathname):
    ## create an empty eBook
    pathname_list = pathname.split("/")
    filename = pathname_list.pop()
    directory = "/".join(pathname_list)
    book = xml2epub.Epub(filename)
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
        filename_tmp = "slixfeedepub"
        book.create_epub(directory, epub_name=filename_tmp)
        pathname_tmp = os.path.join(directory, filename_tmp) + ".epub"
        os.rename(pathname_tmp, pathname)
    except ValueError as error:
        return error
        


def generate_html(text, filename):
    with open(filename, 'w') as file:
        file.write(text)


def generate_markdown(text, filename):
    h2m = html2text.HTML2Text()
    # Convert HTML to Markdown
    markdown = h2m.handle(text)
    with open(filename, 'w') as file:
        file.write(markdown)


def generate_pdf(text, filename):
    try:
        pdfkit.from_string(text, filename)
    except IOError as error:
        return error
    except OSError as error:
        return error


def generate_txt(text, filename):
    text = remove_html_tags(text)
    with open(filename, 'w') as file:
        file.write(text)

def remove_html_tags(data):
    data = BeautifulSoup(data, "lxml").text
    data = data.replace("\n\n", "\n")
    return data

# TODO Add support for eDonkey, Gnutella, Soulseek
async def get_magnet(link):
    parted_link = urlsplit(link)
    queries = parse_qs(parted_link.query)
    query_xt = queries["xt"][0]
    if query_xt.startswith("urn:btih:"):
        filename = queries["dn"][0]
        checksum = query_xt[len("urn:btih:"):]
        torrent = await fetch.magnet(link)
        logging.debug('Attempting to retrieve {} ({})'
                      .format(filename, checksum))
        if not torrent:
            logging.debug(
                "Attempting to retrieve {} from HTTP caching service".format(
                    filename))
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


async def remove_nonexistent_entries(db_file, url, feed):
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
    feed_id = await sqlite.get_feed_id(db_file, url)
    feed_id = feed_id[0]
    items = await sqlite.get_entries_of_feed(db_file, feed_id)
    entries = feed.entries
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
        limit = config.get_setting_value(db_file, "archive")
        await sqlite.maintain_archive(db_file, limit)



async def remove_nonexistent_entries_json(db_file, url, feed):
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
    feed_id = await sqlite.get_feed_id(db_file, url)
    feed_id = feed_id[0]
    items = await sqlite.get_entries_of_feed(db_file, feed_id)
    entries = feed["items"]
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
        limit = config.get_setting_value(db_file, "archive")
        await sqlite.maintain_archive(db_file, limit)