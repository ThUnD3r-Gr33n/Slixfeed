#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
from argparse import ArgumentParser
from asyncio.exceptions import IncompleteReadError
from datetime import date
from getpass import getpass
from http.client import IncompleteRead
from urllib import error
import asyncio
import logging
import sqlite3
from sqlite3 import Error
import sys

import aiohttp
from bs4 import BeautifulSoup
import feedparser
import slixmpp

DBLOCK = asyncio.Lock()


class Slixfeed(slixmpp.ClientXMPP):
    """
    Slixmpp bot that will send updates of feeds it
    receives.
    """
    def __init__(self, jid, password):
        slixmpp.ClientXMPP.__init__(self, jid, password)

        # The session_start event will be triggered when
        # the bot establishes its connection with the server
        # and the XML streams are ready for use. We want to
        # listen for this event so that we we can initialize
        # our roster.
        self.add_event_handler("session_start", self.start)
        self.add_event_handler("session_start", self.send_updates)
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
                print("COMMAND: help")
                print("ACCOUNT: " + str(msg['from']))
                action = print_help()
            # NOTE: Might not need it
            elif message.lower().startswith('feed recent '):
                print("COMMAND: feed recent")
                print("ACCOUNT: " + str(msg['from']))
                action = await initdb(msg['from'].bare, last_entries, message[12:])
            elif message.lower().startswith('feed search '):
                print("COMMAND: feed search")
                print("ACCOUNT: " + str(msg['from']))
                action = await initdb( msg['from'].bare, search_entries, message[12:])
            elif message.lower().startswith('feed list'):
                print("COMMAND: feed list")
                print("ACCOUNT: " + str(msg['from']))
                action = await initdb(msg['from'].bare, list_subscriptions)
            elif message.lower().startswith('feed add '):
                print("COMMAND: feed add")
                print("ACCOUNT: " + str(msg['from']))
                action = await initdb(msg['from'].bare, add_feed, message[9:])
            elif message.lower().startswith('feed remove '):
                print("COMMAND: feed remove")
                print("ACCOUNT: " + str(msg['from']))
                action = await initdb(msg['from'].bare, remove_feed, message[12:])
            elif message.lower().startswith('feed status '):
                print("COMMAND: feed status")
                print("ACCOUNT: " + str(msg['from']))
                action = await initdb(msg['from'].bare, toggle_status, message[12:])
            elif message.lower().startswith('enable'):
                print("COMMAND: enable")
                print("ACCOUNT: " + str(msg['from']))
                action = toggle_state(msg['from'].bare, True)
            elif message.lower().startswith('disable'):
                print("COMMAND: disable")
                print("ACCOUNT: " + str(msg['from']))
                action = toggle_state(msg['from'].bare, False)
            else:
                action = 'Unknown command. Press "help" for list of commands'
            msg.reply(action).send()

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
                    await initdb(jid, download_updates)
            await asyncio.sleep(9)

    async def send_updates(self, event):
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
                        new = await initdb(
                            jid,
                            get_unread
                        )
                        if new:
                            msg = self.make_message(
                                mto=jid,
                                mbody=new,
                                mtype='chat'
                            )
                            msg.send()
            await asyncio.sleep(60 * 3)


def print_help():
    msg = ("Slixfeed - News syndication bot for Jabber/XMPP \n"
           "\n"
           "DESCRIPTION: \n"
           " Slixfeed is an aggregator bot for online news feeds. \n"
           "\n"
           "BASIC USAGE: \n"
           " enable \n"
           "   Send updates. \n"
           " disable \n"
           "   Stop sending updates. \n"
           " feed list \n"
           "   List subscriptions list. \n"
           "\n"
           "EDIT OPTIONS: \n"
           " feed add URL \n"
           "   Add URL to the subscriptions list. \n"
           " feed remove ID \n"
           "   Remove feed from subscription list. \n"
           " feed status ID \n"
           "   Toggle update status of feed. \n"
           "\n"
           "SEARCH OPTIONS: \n"
           " feed search TEXT \n"
           "   Search news items by given keywords. \n"
           " feed recent N \n"
           "   List recent N news items (up to 50 items). \n"
           "\n"
           "DOCUMENTATION: \n"
           " Slixfeed \n"
           "   https://gitgud.io/sjehuda/slixfeed \n"
           " Slixmpp \n"
           "   https://slixmpp.readthedocs.io/ \n"
           " feedparser \n"
           "   https://pythonhosted.org/feedparser")
    return msg


# Function from buku
# https://github.com/jarun/buku
# Arun Prakash Jana (jarun)
# Dmitry Marakasov (AMDmi3)
def get_default_dbdir():
    """Determine the directory path where dbfile will be stored.

    If $XDG_DATA_HOME is defined, use it
    else if $HOME exists, use it
    else if the platform is Windows, use %APPDATA%
    else use the current directory.

    Returns
    -------
    str
    Path to database file.
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
    db_dir = get_default_dbdir()
    if not os.path.isdir(db_dir):
        os.mkdir(db_dir)
    db_file = os.path.join(db_dir, r"{}.db".format(jid))
    create_tables(db_file)

    if message:
        return await callback(db_file, message)
    else:
        return await callback(db_file)


def create_tables(db_file):
    with create_connection(db_file) as conn:
        feeds_table_sql = """
            CREATE TABLE IF NOT EXISTS feeds (
                id integer PRIMARY KEY,
                name text,
                address text NOT NULL,
                enabled integer NOT NULL,
                scanned text,
                updated text,
                status integer,
                valid integer
            ); """
        entries_table_sql = """
            CREATE TABLE IF NOT EXISTS entries (
                id integer PRIMARY KEY,
                title text NOT NULL,
                summary text NOT NULL,
                link text NOT NULL,
                source text,
                read integer
            ); """

        c = conn.cursor()
        c.execute(feeds_table_sql)
        c.execute(entries_table_sql)


def create_connection(db_file):
    """
    Create a database connection to the SQLite database
    specified by db_file
    :param db_file: database file
    :return: Connection object or None
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)
    return conn


async def download_updates(db_file):
    with create_connection(db_file) as conn:
        urls = await get_subscriptions(conn)

    for url in urls:
        source = url[0]
        res = await download_feed(source)

        sql = "UPDATE feeds SET status = :status, scanned = :scanned WHERE address = :url"
        async with DBLOCK:
            with conn:
                cur = conn.cursor()
                cur.execute(sql, {"status": res[1], "scanned": date.today(), "url": source})

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
                sql = "UPDATE feeds SET valid = :validity WHERE address = :url"
                async with DBLOCK:
                    with conn:
                        cur = conn.cursor()
                        cur.execute(sql, {"validity": valid, "url": source})
            except (IncompleteReadError, IncompleteRead, error.URLError) as e:
                print(e)
                return
        # TODO Place these couple of lines back down
        # NOTE Need to correct the SQL statement to do so
        entries = feed.entries
        length = len(entries)
        async with DBLOCK:
            with conn:
                await remove_entry(conn, source, length)

        for entry in entries:
            if entry.has_key("title"):
                title = entry.title
            else:
                title = feed["feed"]["title"]
            link = source if not entry.link else entry.link
            with conn:
                exist = await check_entry(conn, title, link)

            if not exist:
                if entry.has_key("summary"):
                    summary = entry.summary
                    # Remove HTML tags
                    summary = BeautifulSoup(summary, "lxml").text
                    # TODO Limit text length
                    summary = summary.replace("\n\n", "\n")[:300] + "  ‍⃨"
                else:
                    summary = '*** No summary ***'
                    #print('~~~~~~summary not in entry')
                entry = (title, summary, link, source, 0);
                async with DBLOCK:
                    with conn:
                        await add_entry(conn, entry)
                        await set_date(conn, source)


async def download_feed(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            status = response.status
            if response.status == 200:
                doc = await response.text()
                return [doc, status]
            else:
                return [False, status]


async def check_feed(conn, url):
    """
    Check whether a feed exists
    Query for feeds by url
    :param conn:
    :param url:
    :return: row
    """
    cur = conn.cursor()
    sql = "SELECT id FROM feeds WHERE address = ?"
    cur.execute(sql, (url,))
    return cur.fetchone()


async def add_feed(db_file, url):
    """
    Add a new feed into the feeds table
    :param conn:
    :param feed:
    :return: string
    """
    #TODO consider async with DBLOCK
    #conn = create_connection(db_file)
    with create_connection(db_file) as conn:
        exist = await check_feed(conn, url)

    if not exist:
        res = await download_feed(url)
    else:
        return "News source is already listed in the subscription list"

    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            if res[0]:
                feed = feedparser.parse(res[0])
                if feed.bozo:
                    feed = (url, 1, res[1], 0)
                    sql = """INSERT INTO feeds(address,enabled,status,valid)
                             VALUES(?,?,?,?) """
                    cur.execute(sql, feed)
                    bozo = ("WARNING: Bozo detected. Failed to load URL.")
                    print(bozo)
                    return "Failed to parse URL as feed"
                else:
                    title = feed["feed"]["title"]
                    feed = (title, url, 1, res[1], 1)
                    sql = """INSERT INTO feeds(name,address,enabled,status,valid)
                             VALUES(?,?,?,?,?) """
                    cur.execute(sql, feed)
            else:
                feed = (url, 1, res[1], 0)
                sql = "INSERT INTO feeds(address,enabled,status,valid) VALUES(?,?,?,?) "
                cur.execute(sql, feed)
                return "Failed to get URL.  HTTP Error {}".format(res[1])

    source = title if title else '<' + url + '>'
    msg = 'News source "{}" has been added to subscriptions list'.format(source)
    return msg


async def remove_feed(db_file, ix):
    """
    Delete a feed by feed id
    :param conn:
    :param id: id of the feed
    :return: string
    """
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = "SELECT address FROM feeds WHERE id = ?"
        url = cur.execute(sql, (ix,))
        for i in url:
            url = i[0]
        sql = "DELETE FROM entries WHERE source = ?"
        cur.execute(sql, (url,))
        sql = "DELETE FROM feeds WHERE id = ?"
        cur.execute(sql, (ix,))
        return """News source <{}> has been removed from subscriptions list
               """.format(url)


async def get_unread(db_file):
    """
    Check read status of entry
    :param conn:
    :param id: id of the entry
    :return: string
    """
    async with DBLOCK:
        with create_connection(db_file) as conn:
            entry = []
            cur = conn.cursor()
            sql = "SELECT id FROM entries WHERE read = 0"
            ix = cur.execute(sql).fetchone()
            if ix is None:
                return False
            ix = ix[0]
            sql = "SELECT title FROM entries WHERE id = :id"
            cur.execute(sql, (ix,))
            title = cur.fetchone()[0]
            entry.append(title)
            sql = "SELECT summary FROM entries WHERE id = :id"
            cur.execute(sql, (ix,))
            summary = cur.fetchone()[0]
            entry.append(summary)
            sql = "SELECT link FROM entries WHERE id = :id"
            cur.execute(sql, (ix,))
            link = cur.fetchone()[0]
            entry.append(link)
            entry = "{}\n\n{}\n\nLink to article:\n{}".format(entry[0], entry[1], entry[2])
            await mark_as_read(cur, ix)
        return entry


async def mark_as_read(cur, ix):
    """
    Set read status of entry
    :param cur:
    :param ix: index of the entry
    """
    sql = "UPDATE entries SET summary = '', read = 1 WHERE id = ?"
    cur.execute(sql, (ix,))


# TODO mark_all_read for entries of feed
async def toggle_status(db_file, ix):
    """
    Set status of feed
    :param conn:
    :param id: id of the feed
    :return: string
    """
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = "SELECT name FROM feeds WHERE id = :id"
            cur.execute(sql, (ix,))
            title = cur.fetchone()[0]
            sql = "SELECT enabled FROM feeds WHERE id = ?"
            # NOTE [0][1][2]
            cur.execute(sql, (ix,))
            status = cur.fetchone()[0]
            # FIXME always set to 1
            # NOTE Maybe because is not integer
            # TODO Reset feed table before further testing
            if status == 1:
                status = 0
                notice =  "News updates for '{}' are now disabled".format(title)
            else:
                status = 1
                notice =  "News updates for '{}' are now enabled".format(title)
            sql = "UPDATE feeds SET enabled = :status WHERE id = :id"
            cur.execute(sql, {"status": status, "id": ix})
    return notice


def toggle_state(jid, state):
    """
    Set status of update
    :param jid: jid of the user
    :param state: boolean
    :return:
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


async def set_date(conn, url):
    """
    Set last update date of feed
    :param url: url of the feed
    :return:
    """
    today = date.today()
    cur = conn.cursor()
    sql = "UPDATE feeds SET updated = :today WHERE address = :url"
    cur.execute(sql, {"today": today, "url": url})


async def get_subscriptions(conn):
    """
    Query feeds
    :param conn:
    :return: rows (tuple)
    """
    cur = conn.cursor()
    sql = "SELECT address FROM feeds WHERE enabled = 1"
    result = cur.execute(sql)
    return result


async def list_subscriptions(db_file):
    """
    Query feeds
    :param conn:
    :return: rows (string)
    """
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = "SELECT name, address, updated, id, enabled FROM feeds"
        results = cur.execute(sql)

    feeds_list = "List of subscriptions: \n"
    counter = 0
    for result in results:
        counter += 1
        feeds_list += """\n{} \n{} \nLast updated: {} \nID: {} [{}]
        """.format(str(result[0]), str(result[1]), str(result[2]),
                   str(result[3]), str(result[4]))
    if counter:
        return feeds_list + "\n Total of {} subscriptions".format(counter)
    else:
        msg = ("List of subscriptions is empty. \n"
               "To add feed, send a message as follows: \n"
               "feed add URL \n"
               "Example: \n"
               "feed add https://reclaimthenet.org/feed/")
        return msg


async def last_entries(db_file, num):
    """
    Query feeds
    :param conn:
    :param num: integer
    :return: rows (string)
    """
    num = int(num)
    if num > 50:
        num = 50
    elif num < 1:
        num = 1
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = "SELECT title, link FROM entries ORDER BY ROWID DESC LIMIT {}".format(num)
        results = cur.execute(sql)

    titles_list = "Recent {} titles: \n".format(num)
    for result in results:
        titles_list += "\n{} \n{}".format(str(result[0]), str(result[1]))
    return titles_list


async def search_entries(db_file, query):
    """
    Query feeds
    :param conn:
    :param query: string
    :return: rows (string)
    """
    if len(query) < 2:
        return "Please enter at least 2 characters to search"

    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = "SELECT title, link FROM entries WHERE title LIKE '%{}%' LIMIT 50".format(query)
        results = cur.execute(sql)

    results_list = "Search results for '{}': \n".format(query)
    counter = 0
    for result in results:
        counter += 1
        results_list += """\n{} \n{}
        """.format(str(result[0]), str(result[1]))
    if counter:
        return results_list + "\n Total of {} results".format(counter)
    else:
        return "No results found for: {}".format(query)


async def check_entry(conn, title, link):
    """
    Check whether an entry exists
    Query entries by title and link
    :param conn:
    :param link:
    :param title:
    :return: row
    """
    cur = conn.cursor()
    sql = "SELECT id FROM entries WHERE title = :title and link = :link"
    cur.execute(sql, {"title": title, "link": link})
    return cur.fetchone()


async def add_entry(conn, entry):
    """
    Add a new entry into the entries table
    :param conn:
    :param entry:
    :return:
    """
    sql = """ INSERT INTO entries(title,summary,link,source,read)
              VALUES(?,?,?,?,?) """
    cur = conn.cursor()
    cur.execute(sql, entry)


async def remove_entry(conn, source, length):
    """
    Maintain list of entries
    Check the number returned by feed and delete
    existing entries up to the same returned amount
    :param conn:
    :param source:
    :param length:
    :return:
    """
    cur = conn.cursor()
    # FIXED
    # Dino empty titles are not counted https://dino.im/index.xml
    # SOLVED
    # Add text if is empty
    # title = '*** No title ***' if not entry.title else entry.title
    sql = "SELECT count(id) FROM entries WHERE source = ?"
    count = cur.execute(sql, (source,))
    count = cur.fetchone()[0]
    limit = count - length
    if limit:
        limit = limit;
        sql = """DELETE FROM entries WHERE id IN (
                 SELECT id FROM entries
                 WHERE source = :source
                 ORDER BY id
                 ASC LIMIT :limit)"""
        cur.execute(sql, {"source": source, "limit": limit})


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
