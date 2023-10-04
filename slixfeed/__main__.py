#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# TODO
#
# 0) sql prepared statements
# 1) Autodetect feed:
#    if page is not feed (or HTML) and contains <link rel="alternate">
# 2) OPML import/export
# 3) 2022-12-30 reduce async to (maybe) prevent inner lock. async on task: commands, downloader, updater

# vars and their meanings:
# jid = Jabber ID (XMPP)
# res = response (HTTP)

import os
from argparse import ArgumentParser
from asyncio.exceptions import IncompleteReadError
from datetime import date
from getpass import getpass
from http.client import IncompleteRead
from urllib import error
import asyncio
import logging
import sys
import time

import aiohttp
from bs4 import BeautifulSoup
from xml.etree.ElementTree import ElementTree, ParseError
from urllib.parse import urlparse
from lxml import html
import feedparser
import slixmpp

# from eliot import start_action, to_file
# # to_file(open("slixfeed.log", "w"))
# # with start_action(action_type="set_date()", jid=jid):
# # with start_action(action_type="message()", msg=msg):

import database


class Slixfeed(slixmpp.ClientXMPP):
    """
    Slixmpp news bot that will send updates
    from feeds it receives.
    """
    def __init__(self, jid, password):
        slixmpp.ClientXMPP.__init__(self, jid, password)

        # The session_start event will be triggered when
        # the bot establishes its connection with the server
        # and the XML streams are ready for use. We want to
        # listen for this event so that we we can initialize
        # our roster.
        self.add_event_handler("session_start", self.start)
        self.add_event_handler("session_start", self.send_update)
        self.add_event_handler("session_start", self.send_status)
        self.add_event_handler("session_start", self.check_updates)

        # The message event is triggered whenever a message
        # stanza is received. Be aware that that includes
        # MUC messages and error messages.
        self.add_event_handler("message", self.message)
        self.add_event_handler("disconnected", self.reconnect)

    async def start(self, event):
        """
        Process the session_start event.

        Typical actions for the session_start event are
        requesting the roster and broadcasting an initial
        presence stanza.

        Arguments:
            event -- An empty dictionary. The session_start
                     event does not provide any additional
                     data.
        """
        self.send_presence()
        await self.get_roster()

    async def message(self, msg):
        """
        Process incoming message stanzas. Be aware that this also
        includes MUC messages and error messages. It is usually
        a good idea to check the messages's type before processing
        or sending replies.

        Arguments:
            msg -- The received message stanza. See the documentation
                   for stanza objects and the Message stanza to see
                   how it may be used.
        """
        if msg['type'] in ('chat', 'normal'):
            message = " ".join(msg['body'].split())
            if message.lower().startswith('help'):
                action = print_help()
            # NOTE: Might not need it
            elif message.lower().startswith('recent '):
                action = await initdb(msg['from'].bare, database.last_entries, message[7:])
            elif message.lower().startswith('search '):
                action = await initdb( msg['from'].bare, database.search_entries, message[7:])
            elif message.lower().startswith('list'):
                action = await initdb(msg['from'].bare, database.list_subscriptions)
            elif message.lower().startswith('add '):
                action = await initdb(msg['from'].bare, add_feed, message[4:])
            elif message.lower().startswith('remove '):
                action = await initdb(msg['from'].bare, database.remove_feed, message[7:])
            elif message.lower().startswith('status '):
                action = await initdb(msg['from'].bare, database.toggle_status, message[7:])
            elif message.lower().startswith('unread'):
                action = await initdb(msg['from'].bare, database.statistics)
            elif message.lower().startswith('enable'):
                action = toggle_state(msg['from'].bare, True)
            elif message.lower().startswith('disable'):
                action = toggle_state(msg['from'].bare, False)
            else:
                action = 'Unknown command. Press "help" for list of commands'
            msg.reply(action).send()

            print("COMMAND:", message)
            print("ACCOUNT: " + str(msg['from']))

    async def check_updates(self, event):
        while True:
            print("Checking update")
            db_dir = get_default_dbdir()
            if not os.path.isdir(db_dir):
                msg = ("Slixfeed can not work without a database. \n"
                       "To create a database, follow these steps: \n"
                       "Add Slixfeed contact to your roster \n"
                       "Send a feed to the bot by: \n"
                       "feed add https://reclaimthenet.org/feed/")
                print(msg)
            else:
                files = os.listdir(db_dir)
                for file in files:
                    jid = file[:-3]
                    print("download_updates",jid)
                    await initdb(jid, download_updates)
            await asyncio.sleep(90)

    async def send_update(self, event):
        while True:
            db_dir = get_default_dbdir()
            if not os.path.isdir(db_dir):
                msg = ("Slixfeed can not work without a database. \n"
                       "To create a database, follow these steps: \n"
                       "Add Slixfeed contact to your roster \n"
                       "Send a feed to the bot by: \n"
                       "feed add https://reclaimthenet.org/feed/")
                print(msg)
            else:
                os.chdir(db_dir)
                files = os.listdir()
                for file in files:
                    if not file.endswith('.db-jour.db'):
                        jid = file[:-3]
                        print("get_entry_unread",jid)

                        new = await initdb(
                            jid,
                            database.get_entry_unread
                        )

                        if new:
                            msg = self.send_message(
                                mto=jid,
                                mbody=new,
                                mtype='chat'
                            )

                            unread = await initdb(
                                jid,
                                database.get_number_of_entries_unread
                            )

                            if unread:
                                msg_status = ('📰 News items:', str(unread))
                                msg_status = ' '.join(msg_status)
                            else:
                                msg_status = '🗞 No News'

                            print(msg_status, 'for', jid)

                            # Send status message
                            self.send_presence(
                                pstatus=msg_status,
                                pto=jid,
                                #pfrom=None
                            )

            # await asyncio.sleep(15)
            await asyncio.sleep(60 * 3)

    async def send_status(self, event):
        while True:
            db_dir = get_default_dbdir()
            if not os.path.isdir(db_dir):
                msg = ("Slixfeed can not work without a database. \n"
                       "To create a database, follow these steps: \n"
                       "Add Slixfeed contact to your roster \n"
                       "Send a feed to the bot by: \n"
                       "feed add https://reclaimthenet.org/feed/")
                print(msg)
            else:
                files = os.listdir(db_dir)
                for file in files:
                    jid = file[:-3]

            await asyncio.sleep(60)


def print_help():
    """
    Print help manual.
    """
    msg = ("Slixfeed - News syndication bot for Jabber/XMPP \n"
           "\n"
           "DESCRIPTION: \n"
           " Slixfeed is a news aggregator bot for online news feeds. \n"
           " Supported filetypes: Atom, RDF and RSS. \n"
           "\n"
           "BASIC USAGE: \n"
           " enable \n"
           "   Send updates. \n"
           " disable \n"
           "   Stop sending updates. \n"
           " batch N \n"
           "   Send N updates on ech interval. \n"
           " interval N \n"
           "   Send an update each N minutes. \n"
           " feed list \n"
           "   List subscriptions. \n"
           "\n"
           "EDIT OPTIONS: \n"
           " add URL \n"
           "   Add URL to subscription list. \n"
           " remove ID \n"
           "   Remove feed from subscription list. \n"
           " status ID \n"
           "   Toggle update status of feed. \n"
           "\n"
           "SEARCH OPTIONS: \n"
           " search TEXT \n"
           "   Search news items by given keywords. \n"
           " recent N \n"
           "   List recent N news items (up to 50 items). \n"
           "\n"
           "STATISTICS OPTIONS: \n"
           " analyses \n"
           "   Show report and statistics of feeds. \n"
           " obsolete \n"
           "   List feeds that are not available. \n"
           " unread \n"
           "   Print number of unread news items. \n"
           "\n"
           "BACKUP OPTIONS: \n"
           " export opml \n"
           "   Send an OPML file with your feeds. \n"
           " backup news html\n"
           "   Send an HTML formatted file of your news items. \n"
           " backup news md \n"
           "   Send a Markdown file of your news items. \n"
           " backup news text \n"
           "   Send a Plain Text file of your news items. \n"
           "\n"
           "DOCUMENTATION: \n"
           " Slixfeed \n"
           "   https://gitgud.io/sjehuda/slixfeed \n"
           " Slixmpp \n"
           "   https://slixmpp.readthedocs.io/ \n"
           " feedparser \n"
           "   https://pythonhosted.org/feedparser")
    return msg


# Function from jarun/buku
# Arun Prakash Jana (jarun)
# Dmitry Marakasov (AMDmi3)
def get_default_dbdir():
    """Determine the directory path where dbfile will be stored.

    If $XDG_DATA_HOME is defined, use it
    else if $HOME exists, use it
    else if the platform is Windows, use %APPDATA%
    else use the current directory.

    :return: Path to database file.
    
    Note
    ----
    This code was taken from the buku project.
    """
#    data_home = xdg.BaseDirectory.xdg_data_home
    data_home = os.environ.get('XDG_DATA_HOME')
    if data_home is None:
        if os.environ.get('HOME') is None:
            if sys.platform == 'win32':
                data_home = os.environ.get('APPDATA')
                if data_home is None:
                    return os.path.abspath('.')
            else:
                return os.path.abspath('.')
        else:
            data_home = os.path.join(os.environ.get('HOME'), '.local', 'share')
    return os.path.join(data_home, 'slixfeed')


# TODO Perhaps this needs to be executed
# just once per program execution
async def initdb(jid, callback, message=None):
    """
    Callback function to instantiate action on database.
    
    :param jid: JID (Jabber ID).
    :param callback: Function name.
    :param massage: Optional kwarg when a message is a part or required argument.
    """
    db_dir = get_default_dbdir()
    if not os.path.isdir(db_dir):
        os.mkdir(db_dir)
    db_file = os.path.join(db_dir, r"{}.db".format(jid))
    database.create_tables(db_file)

    if message:
        return await callback(db_file, message)
    else:
        return await callback(db_file)

# NOTE I don't think there should be "return"
# because then we might stop scanning next URLs
async def download_updates(db_file):
    """
    Chack feeds for new entries.
    
    :param db_file: Database filename.
    """
    urls = await database.get_subscriptions(db_file)

    for url in urls:
        # print("for url in urls")
        source = url[0]
        # print("source: ", source)
        res = await download_feed(source)
        # TypeError: 'NoneType' object is not subscriptable
        if res is None:
            # Skip to next feed
            # urls.next()
            # next(urls)
            continue
        
        await database.update_source_status(db_file, res[1], source)

        if res[0]:
            try:
                feed = feedparser.parse(res[0])
                if feed.bozo:
                    bozo = ("WARNING: Bozo detected for feed <{}>. "
                            "For more information, visit "
                            "https://pythonhosted.org/feedparser/bozo.html"
                            .format(source))
                    print(bozo)
                    valid = 0
                else:
                    valid = 1

                await database.update_source_validity(db_file, source, valid)
            except (IncompleteReadError, IncompleteRead, error.URLError) as e:
                print(e)
                # return
        # TODO Place these couple of lines back down
        # NOTE Need to correct the SQL statement to do so
        # NOT SURE WHETHER I MEANT THE LINES ABOVE OR BELOW
        
        if res[1] == 200:
        # NOT SURE WHETHER I MEANT THE LINES ABOVE OR BELOW
        # TODO Place these couple of lines back down
        # NOTE Need to correct the SQL statement to do so
            entries = feed.entries
            # length = len(entries)
            # await database.remove_entry(db_file, source, length)
            await database.remove_nonexistent_entries(db_file, feed, source)

            new_entry = 0
            for entry in entries:

                if entry.has_key("title"):
                    title = entry.title
                else:
                    title = feed["feed"]["title"]

                if entry.has_key("link"):
                    link = entry.link
                else:
                    link = source
                    # print('source:', source)

                exist = await database.check_entry_exist(db_file, title, link)

                if not exist:
                    new_entry = new_entry + 1
                    # TODO Enhance summary
                    if entry.has_key("summary"):
                        summary = entry.summary
                        # Remove HTML tags
                        summary = BeautifulSoup(summary, "lxml").text
                        # TODO Limit text length
                        summary = summary.replace("\n\n", "\n")[:300] + "  ‍⃨"
                    else:
                        summary = '*** No summary ***'
                    entry = (title, summary, link, source, 0);
                    await database.add_entry_and_set_date(db_file, source, entry)
            # print("### added", new_entry, "entries")


async def download_feed(url):
    """
    Download content of given URL.
    
    :param url: URL.
    :return: Document or error message.
    """
    # print("download_feed")
    # time.sleep(1)
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession() as session:
    # async with aiohttp.ClientSession(trust_env=True) as session:
        try:
            async with session.get(url, timeout=timeout) as response:
                status = response.status
                if response.status == 200:
                    try:
                        doc = await response.text()
                        # print (response.content_type)
                        return [doc, status]
                    except:
                        return [False, "The content of this document doesn't appear to be textual"]
                else:
                    return [False, "HTTP Error: " + str(status)]
        except aiohttp.ClientError as e:
            print('Error', str(e))
            return [False, "Error: " + str(e)]
        except asyncio.TimeoutError as e:
            print('Timeout', str(e))
            return [False, "Timeout"]


async def add_feed(db_file, url):
    """
    Check whether feed exist, otherwise process it.

    :param db_file: Database filename.
    :param url: URL.
    :return: Status message.
    """
    exist = await database.check_feed_exist(db_file, url)
    
    if not exist:
        res = await download_feed(url)
        if res[0]:
            feed = feedparser.parse(res[0])
            if feed.bozo:
                bozo = ("WARNING: Bozo detected. Failed to load <{}>.".format(url))
                print(bozo)
                try:
                    # tree = etree.fromstring(res[0]) # etree is for xml
                    tree = html.fromstring(res[0])
                except:
                    return "Failed to parse URL <{}> as feed".format(url)

                print("RSS Auto-Discovery Engaged")
                xpath_query = """//link[(@rel="alternate") and (@type="application/atom+xml" or @type="application/rdf+xml" or @type="application/rss+xml")]"""
                # xpath_query = """//link[(@rel="alternate") and (@type="application/atom+xml" or @type="application/rdf+xml" or @type="application/rss+xml")]/@href"""
                # xpath_query = "//link[@rel='alternate' and @type='application/atom+xml' or @rel='alternate' and @type='application/rss+xml' or @rel='alternate' and @type='application/rdf+xml']/@href"
                feeds = tree.xpath(xpath_query)
                if len(feeds) > 1:
                    msg = "RSS Auto-Discovery has found {} feeds:\n\n".format(len(feeds))
                    for feed in feeds:
                        # # The following code works;
                        # # The following code will catch
                        # # only valid resources (i.e. not 404);
                        # # The following code requires more bandwidth.
                        # res = await download_feed(feed)
                        # if res[0]:
                        #     disco = feedparser.parse(res[0])
                        #     title = disco["feed"]["title"]
                        #     msg += "{} \n {} \n\n".format(title, feed)
                        feed_name = feed.xpath('@title')[0]
                        feed_addr = feed.xpath('@href')[0]
                        msg += "{}\n{}\n\n".format(feed_name, feed_addr)
                    msg += "The above feeds were extracted from\n{}".format(url)
                    return msg
                elif feeds:
                    url = feeds[0].xpath('@href')[0]
                    # Why wouldn't add_feed return a message
                    # upon success unless return is explicitly
                    # mentioned, yet upon failure it wouldn't?
                    return await add_feed(db_file, url)

                # Search for feeds by file extension and path
                paths = [
                    "/app.php/feed", # phpbb
                    "/atom",
                    "/atom.php",
                    "/atom.xml",
                    "/content-feeds/",
                    "/external.php?type=RSS2",
                    "/feed", # good practice
                    "/feed.atom",
                    # "/feed.json",
                    "/feed.php",
                    "/feed.rdf",
                    "/feed.rss",
                    "/feed.xml",
                    "/feed/atom/",
                    "/feeds/news_feed",
                    "/feeds/rss/news.xml.php",
                    "/forum_rss.php",
                    "/index.php/feed",
                    "/index.php?type=atom;action=.xml", #smf
                    "/index.php?type=rss;action=.xml", #smf
                    "/index.rss",
                    "/latest.rss",
                    "/news",
                    "/news.xml",
                    "/news.xml.php",
                    "/news/feed",
                    "/posts.rss", # discourse
                    "/rdf",
                    "/rdf.php",
                    "/rdf.xml",
                    "/rss",
                    # "/rss.json",
                    "/rss.php",
                    "/rss.xml",
                    "/timeline.rss",
                    "/xml/feed.rss",
                    # "?format=atom",
                    # "?format=rdf",
                    # "?format=rss",
                    # "?format=xml"
                    ]

                print("RSS Scan Mode Engaged")
                feeds = {}
                for path in paths:
                    # xpath_query = "//*[@*[contains(.,'{}')]]".format(path)
                    xpath_query = "//a[contains(@href,'{}')]".format(path)
                    addresses = tree.xpath(xpath_query)
                    parted_url = urlparse(url)
                    for address in addresses:
                        address = address.xpath('@href')[0]
                        if address.startswith('/'):
                            address = parted_url.scheme + '://' + parted_url.netloc + address
                        res = await download_feed(address)
                        if res[1] == 200:
                            try:
                                feeds[address] = feedparser.parse(res[0])["feed"]["title"]
                            except:
                                continue
                if len(feeds) > 1:
                    msg = "RSS URL scan has found {} feeds:\n\n".format(len(feeds))
                    for feed in feeds:
                        # try:
                        #     res = await download_feed(feed)
                        # except:
                        #     continue
                        feed_name = feeds[feed]
                        feed_addr = feed
                        msg += "{}\n{}\n\n".format(feed_name, feed_addr)
                    msg += "The above feeds were extracted from\n{}".format(url)
                    return msg
                elif feeds:
                    url = list(feeds)[0]
                    return await add_feed(db_file, url)

                # (HTTP) Request(s) Paths
                print("RSS Arbitrary Mode Engaged")
                feeds = {}
                parted_url = urlparse(url)
                for path in paths:
                    address = parted_url.scheme + '://' + parted_url.netloc + path
                    res = await download_feed(address)
                    if res[1] == 200:
                        # print(feedparser.parse(res[0])["feed"]["title"])
                        # feeds[address] = feedparser.parse(res[0])["feed"]["title"]
                        try:
                            title = feedparser.parse(res[0])["feed"]["title"]
                        except:
                            title = '*** No Title ***'
                        feeds[address] = title

                    # Check whether URL has path (i.e. not root)
                    if parted_url.path.split('/')[1]:
                        paths.extend([".atom", ".feed", ".rdf", ".rss"]) if '.rss' not in paths else -1
                        # if paths.index('.rss'):
                        #     paths.extend([".atom", ".feed", ".rdf", ".rss"])
                        address = parted_url.scheme + '://' + parted_url.netloc + '/' + parted_url.path.split('/')[1] + path
                        res = await download_feed(address)
                        if res[1] == 200:
                            print('ATTENTION')
                            print(address)
                            try:
                                title = feedparser.parse(res[0])["feed"]["title"]
                            except:
                                title = '*** No Title ***'
                            feeds[address] = title
                if len(feeds) > 1:
                    msg = "RSS URL discovery has found {} feeds:\n\n".format(len(feeds))
                    for feed in feeds:
                        feed_name = feeds[feed]
                        feed_addr = feed
                        msg += "{}\n{}\n\n".format(feed_name, feed_addr)
                    msg += "The above feeds were extracted from\n{}".format(url)
                    return msg
                elif feeds:
                    url = list(feeds)[0]
                    return await add_feed(db_file, url)
                else:
                    return "No news feeds were found for URL <{}>.".format(url)
            else:
                return await database.add_feed(db_file, feed, url, res)
        else:
            return "Failed to get URL <{}>.  Reason: {}".format(url, res[1])
    else:
        ix = exist[0]
        return "News source <{}> is already listed in the subscription list at index {}".format(url, ix)


def toggle_state(jid, state):
    """
    Set status of update.
    
    :param jid: JID (Jabber ID).
    :param state: True or False.
    :return: Status message.
    """
    db_dir = get_default_dbdir()
    db_file = os.path.join(db_dir, r"{}.db".format(jid))
    bk_file = os.path.join(db_dir, r"{}.db.bak".format(jid))

    if state:
        if os.path.exists(db_file):
            return "Updates are already enabled"
        elif os.path.exists(bk_file):
            os.renames(bk_file, db_file)
            return "Updates are now enabled"
    else:
        if os.path.exists(bk_file):
            return "Updates are already disabled"
        elif os.path.exists(db_file):
            os.renames(db_file, bk_file)
            return "Updates are now disabled"


if __name__ == '__main__':
    # Setup the command line arguments.
    parser = ArgumentParser(description=Slixfeed.__doc__)

    # Output verbosity options.
    parser.add_argument(
         "-q", "--quiet", help="set logging to ERROR",
         action="store_const", dest="loglevel",
         const=logging.ERROR, default=logging.INFO
    )
    parser.add_argument(
        "-d", "--debug", help="set logging to DEBUG",
        action="store_const", dest="loglevel",
        const=logging.DEBUG, default=logging.INFO
    )

    # JID and password options.
    parser.add_argument("-j", "--jid", dest="jid",
                        help="JID to use")
    parser.add_argument("-p", "--password", dest="password",
                        help="password to use")

    args = parser.parse_args()

    # Setup logging.
    logging.basicConfig(level=args.loglevel,
                        format='%(levelname)-8s %(message)s')

    if args.jid is None:
        args.jid = input("Username: ")
    if args.password is None:
        args.password = getpass("Password: ")

    # Setup the Slixfeed and register plugins. Note that while plugins may
    # have interdependencies, the order in which you register them does
    # not matter.
    xmpp = Slixfeed(args.jid, args.password)
    xmpp.register_plugin('xep_0004') # Data Forms
    xmpp.register_plugin('xep_0030') # Service Discovery
    xmpp.register_plugin('xep_0045') # Multi-User Chat
    xmpp.register_plugin('xep_0060') # PubSub
    xmpp.register_plugin('xep_0199') # XMPP Ping

    # Connect to the XMPP server and start processing XMPP stanzas.
    xmpp.connect()
    xmpp.process()
