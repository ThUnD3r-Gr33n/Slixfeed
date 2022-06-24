#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun May 15 17:09:05 2022

@author: Schimon Jehudah, Adv.
"""
from argparse import ArgumentParser
from asyncio.exceptions import IncompleteReadError
from bs4 import BeautifulSoup
from datetime import date
from getpass import getpass
from http.client import IncompleteRead
from urllib import error
#from urllib.parse import urlparse
#from xdg import BaseDirectory

import asyncio
import feedparser
import logging
import os
import slixmpp
import sqlite3
from sqlite3 import Error
import sys
#import xdg

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

        # The message event is triggered whenever a message
        # stanza is received. Be aware that that includes
        # MUC messages and error messages.
        self.add_event_handler("message", self.message)
        self.add_event_handler("disconnected", self.disconnected)

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

    def disconnected(self):
        print("disconnected")
        return True

    def message(self, msg):
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
            # download_updates(msg['from'])
            message = " ".join(msg['body'].split())
            if message.startswith('help'):
                action = print_help()
            # NOTE: Might not need it
            elif message.startswith('feed update'):
                action = "/me is scanning feeds for updates..."
                msg.reply(action).send()
                initdb(msg['from'].bare,
                                False,
                                download_updates)
            elif message.startswith('feed recent '):
                action = initdb(msg['from'].bare, 
                                  message[12:],
                                  last_entries)
            elif message.startswith('feed search '):
                action = initdb(msg['from'].bare, 
                                  message[12:],
                                  search_entries)
            elif message.startswith('feed list'):
                action = initdb(msg['from'].bare, 
                                  False,
                                  list_subscriptions)
            elif message.startswith('feed add '):
                action = initdb(msg['from'].bare,
                                  message[9:],
                                  add_feed)
            elif message.startswith('feed remove '):
                action = initdb(msg['from'].bare,
                                  message[12:],
                                  remove_feed)
            elif message.startswith('feed status '):
                action = initdb(msg['from'].bare,
                                  message[12:],
                                  toggle_status)
            else:
                action = "Unknown command. Press \"help\" for list of commands"
            msg.reply(action).send()

    async def check_updates():
        while True:
            db_dir = get_default_dbdir()
            if not os.path.isdir(db_dir):
            # NOTE: Impossible scenario
                msg = """
                No database directory was found. \n
                To create News database,send these messages to bot: \n
                add feed https://reclaimthenet.org/feed/
                update
                """
                print(msg)
            else:
                os.chdir(db_dir)
                files = os.listdir()
                for file in files:
                    jid = file[:-3]
                    initdb(jid,
                           False,
                           download_updates)
            await asyncio.sleep(30)
            #await asyncio.sleep(60 * 30)
            #await asyncio.sleep(180 * 60)

    async def send_updates(self, event):
        while True:
            db_dir = get_default_dbdir()
            if not os.path.isdir(db_dir):
            # NOTE: Impossible scenario
                msg = """
                No database directory was found. \n
                To create News database,send these messages to bot: \n
                add feed https://reclaimthenet.org/feed/
                update
                """
                print(msg)
            else:
                os.chdir(db_dir)
                files = os.listdir()
                for file in files:
                    jid = file[:-3]
                    new = initdb(jid, False, get_unread)
                    if new:
                        msg = self.make_message(mto=jid, mbody=new,
                                                mtype='chat')
                        msg.send()
                        # today = str(date.today())
                        # news.insert = [0, 'News fetched on: ' + today]
                        #news.append('End of News update')
                        #for new in news:
                            #print("sending to: jid")
                            #print("sending to: " + jid)
                            # self.send_message(mto=jid,
                            #                   mbody=new,
                            #                   mtype='normal').send()
                            #msg = self.make_message(mto=jid,
                            #                  mbody=new,
                            #                  mtype='chat')
                            #print(msg)
                            #msg.send()
            await asyncio.sleep(10)

    #asyncio.ensure_future(check_updates())
    #asyncio.ensure_future(send_updates())

def print_help():
    msg = ("Slixfeed - News syndication bot for Jabber/XMPP \n"
           "\n"
           "DESCRIPTION: \n"
           " Slixfeed is an aggregator bot for online news feeds. \n"
           "\n"
           "BASIC USAGE: \n"
           " feed update \n"
           "   Update subscriptions. \n"
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
           "   List recent N news items. \n"
           "\n"
           "DOCUMENTATION: \n"
           " feedparser \n"
           "   https://pythonhosted.org/feedparser \n"
           " Slixmpp \n"
           "   https://slixmpp.readthedocs.io/")

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
def initdb(jid, message, callback):
    db_dir = get_default_dbdir()
    if not os.path.isdir(db_dir):
        os.mkdir(db_dir)
    os.chdir(db_dir)
    db_file = r"{}.db".format(jid)

    feeds_table_sql = """
        CREATE TABLE IF NOT EXISTS feeds (
            id integer PRIMARY KEY,
            name text,
            address text NOT NULL,
            status integer,
            updated text
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

    # create a database connection
    conn = create_connection(db_file)

    # create tables
    if conn is not None:
        # create projects table
        create_table(conn, feeds_table_sql)
        create_table(conn, entries_table_sql)
    else:
        print("Error! cannot create the database connection.")

    if message:
        return callback(conn, message)
    else:
        return callback(conn)

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

def create_table(conn, create_table_sql):
    """
    Create a table from the create_table_sql statement
    :param conn: Connection object
    :param create_table_sql: a CREATE TABLE statement
    :return:
    """
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except Error as e:
        print(e)

# def setup_info(jid):
# def start_process(jid):
def download_updates(conn):

    with conn:
        # get current date
        #today = date.today()
        urls = get_subscriptions(conn)
        for url in urls:
            #"".join(url)
            source = url[0]
            try:
                feed = feedparser.parse(source)
                if feed.bozo:
                    bozo = ("WARNING: Bozo detected for feed <{}>. "
                            "For more information, visit "
                            "https://pythonhosted.org/feedparser/bozo.html"
                            .format(source))
                    print(bozo)
            except (IncompleteReadError, IncompleteRead, error.URLError) as e:
                print(e)
                continue
            # TODO Place these couple of lines back down
            # NOTE Need to correct the SQL statement to do so
            entries = feed.entries
            length = len(entries)
            remove_entry(conn, source, length)
            for entry in entries:
                title = '*** No title ***' if not entry.title else entry.title
                link = source if not entry.link else entry.link
                exist = check_entry(conn, title, link)
                if not exist:
                    if entry.has_key("summary"):
                        summary = entry.summary
                        # Remove HTML tags
                        summary = BeautifulSoup(summary, "lxml").text
                        # TODO Limit text length
                        summary = summary.replace("\n\n", "\n")
                    else:
                        summary = '*** No summary ***'
                        #print('~~~~~~summary not in entry')
                    entry = (title, summary, link, source, 0);
                    add_entry(conn, entry)
                    set_date(conn, source)
                    #make_message
    #                 message = title + '\n\n' + summary + '\n\nLink: ' + link
    #                 print(message)
    #                 news.append(message)
    #                 print(len(news))
    # return news

def check_feed(conn, url):
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
    print(cur.fetchone())
    return cur.fetchone()

def add_feed(conn, url):
    """
    Add a new feed into the feeds table
    :param conn:
    :param feed:
    :return: string
    """
    #conn = create_connection(db_file)
    exist = check_feed(conn, url)
    if not exist:
        feed = feedparser.parse(url)
        if feed.bozo:
            bozo = ("WARNING: Bozo detected. Failed to load URL.")
            print(bozo)
            return "Failed to parse URL as feed"
        title = feedparser.parse(url)["feed"]["title"]
        feed = (title, url, 1)
        cur = conn.cursor()
        sql = """INSERT INTO feeds(name,address,status)
                 VALUES(?,?,?) """
        cur.execute(sql, feed)
        conn.commit()
        # source = title if not '' else url
        source = title if title else url
    return """News source "{}" has been added to subscriptions list
           """.format(source)

def remove_feed(conn, id):
    """
    Delete a feed by feed id
    :param id: id of the feed
    :return: string
    """
    # You have chose to remove feed (title, url) from your feed list.
    # Enter "delete" to confirm removal.
    #conn = create_connection(db_file)
    cur = conn.cursor()
    sql = "SELECT address FROM feeds WHERE id = ?"
    # NOTE [0][1][2]
    url = cur.execute(sql, (id,))
    for i in url:
        url = i[0]
    sql = "DELETE FROM entries WHERE source = ?"
    cur.execute(sql, (url,))
    sql = "DELETE FROM feeds WHERE id = ?"
    cur.execute(sql, (id,))
    conn.commit()
    return """News source "{}" has been removed from subscriptions list
           """.format(url)

def get_unread(conn):
    """
    Check read status of entry
    :param id: id of the entry
    :return: string
    """
    entry = []
    cur = conn.cursor()
    sql = "SELECT id FROM entries WHERE read = 0"
    #id = cur.execute(sql).fetchone()[0]
    id = cur.execute(sql).fetchone()
    if id is None:
        return False
    id = id[0]
    sql = "SELECT title FROM entries WHERE id = :id"
    cur.execute(sql, (id,))
    title = cur.fetchone()[0]
    entry.append(title)
    sql = "SELECT summary FROM entries WHERE id = :id"
    cur.execute(sql, (id,))
    summary = cur.fetchone()[0]
    entry.append(summary)
    sql = "SELECT link FROM entries WHERE id = :id"
    cur.execute(sql, (id,))
    link = cur.fetchone()[0]
    entry.append(link)
    # columns = ['title', 'summary', 'link']
    # for column in columns:
    #     sql = "SELECT :column FROM entries WHERE id = :id"
    #     cur.execute(sql, {"column": column, "id": id})
    #     str = cur.fetchone()[0]
    #     entry.append(str)
    entry = "{}\n\n{}\n\nMore information at:\n{}".format(entry[0], entry[1], entry[2])
    mark_as_read(conn, id)
    conn.commit()
    return entry

def mark_as_read(conn, id):
    """
    Set read status of entry
    :param id: id of the entry
    :return:
    """
    cur = conn.cursor()
    sql = "UPDATE entries SET summary = '', read = 1 WHERE id = ?"
    cur.execute(sql, (id,))
    conn.commit()
    return

# TODO test
def toggle_status(conn, id):
    """
    Set status of feed
    :param id: id of the feed
    :return: string
    """
    #conn = create_connection(db_file)
    cur = conn.cursor()
    sql = "SELECT name FROM feeds WHERE id = :id"
    cur.execute(sql, (id,))
    title = cur.fetchone()[0]
    sql = "SELECT status FROM feeds WHERE id = ?"
    # NOTE [0][1][2]
    cur.execute(sql, (id,))
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
    sql = "UPDATE feeds SET status = :status WHERE id = :id"
    cur.execute(sql, {"status": status, "id": id})
    conn.commit()
    return notice

def set_date(conn, url):
    """
    Set last update date of feed
    :param url: url of the feed
    :return:
    """
    today = date.today()
    cur = conn.cursor()
    sql = "UPDATE feeds SET updated = :today WHERE address = :url"
    cur.execute(sql, {"today": today, "url": url})
    conn.commit()

def get_subscriptions(conn):
    """
    Query feeds
    :param conn:
    :return: rows (tuple)
    """
    cur = conn.cursor()
    sql = "SELECT address FROM feeds WHERE status = 1"
    result = cur.execute(sql)
    return result

def list_subscriptions(conn):
    """
    Query feeds
    :param conn:
    :return: rows (string)
    """
    cur = conn.cursor()
    #sql = "SELECT id, address FROM feeds"
    sql = "SELECT name, address, updated, id, status FROM feeds"
    results = cur.execute(sql)
    feeds_list = "List of subscriptions: \n"
    for result in results:
        #feeds_list = feeds_list + '\n {}. {}'.format(str(result[0]), str(result[1]))
        feeds_list += """\n{} \n{} \nLast updated: {} \nID: {} [{}]
        """.format(str(result[0]), str(result[1]), str(result[2]),
                   str(result[3]), str(result[4]))
    return feeds_list

def check_entry(conn, title, link):
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

def add_entry(conn, entry):
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
    conn.commit()

def remove_entry(conn, source, length):
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
    #limit = count - length
    limit = count - length
    if limit:
    #if limit > 0:
        limit = limit;
        sql = """DELETE FROM entries WHERE id IN (
                 SELECT id FROM entries
                 WHERE source = :source
                 ORDER BY id
                 ASC LIMIT :limit)"""
        cur.execute(sql, {"source": source, "limit": limit})
        conn.commit()

if __name__ == '__main__':
    # Setup the command line arguments.
    parser = ArgumentParser(description=Slixfeed.__doc__)

    # Output verbosity options.
    parser.add_argument("-q", "--quiet", help="set logging to ERROR",
                        action="store_const", dest="loglevel",
                        const=logging.ERROR, default=logging.INFO)
    parser.add_argument("-d", "--debug", help="set logging to DEBUG",
                        action="store_const", dest="loglevel",
                        const=logging.DEBUG, default=logging.INFO)

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
    xmpp.register_plugin('xep_0030') # Service Discovery
    xmpp.register_plugin('xep_0004') # Data Forms
    xmpp.register_plugin('xep_0060') # PubSub
    xmpp.register_plugin('xep_0199') # XMPP Ping

    # Connect to the XMPP server and start processing XMPP stanzas.
    xmpp.connect()
    xmpp.process()
