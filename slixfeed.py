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
from os import path
from urllib import error
#from urllib.parse import urlparse
#from xdg import BaseDirectory

import aiohttp
import asyncio
import feedparser
import logging
import os
import os.path
import slixmpp
import sqlite3
from sqlite3 import Error
import sys
import time
#import xdg

# offline = False

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
        self.add_event_handler("disconnected", self.reconnect)

    # async def reconnect(self, event):
    #     await asyncio.sleep(10)
    #     offline = True
    #     print(time.strftime("%H:%M:%S"))
    #     print(offline)
    #     self.connect()
    #     #return True

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
                action = await initdb(msg['from'].bare, 
                                  message[12:],
                                  last_entries)
            elif message.lower().startswith('feed search '):
                print("COMMAND: feed search")
                print("ACCOUNT: " + str(msg['from']))
                action = await initdb(msg['from'].bare, 
                                  message[12:],
                                  search_entries)
            elif message.lower().startswith('feed list'):
                print("COMMAND: feed list")
                print("ACCOUNT: " + str(msg['from']))
                action = await initdb(msg['from'].bare, 
                                  False,
                                  list_subscriptions)
            elif message.lower().startswith('feed add '):
                print("COMMAND: feed add")
                print("ACCOUNT: " + str(msg['from']))
                action = await initdb(msg['from'].bare,
                                  message[9:],
                                  add_feed)
            elif message.lower().startswith('feed remove '):
                print("COMMAND: feed remove")
                print("ACCOUNT: " + str(msg['from']))
                action = await initdb(msg['from'].bare,
                                  message[12:],
                                  remove_feed)
            elif message.lower().startswith('feed status '):
                print("COMMAND: feed status")
                print("ACCOUNT: " + str(msg['from']))
                action = await initdb(msg['from'].bare,
                                  message[12:],
                                  toggle_status)
            elif message.lower().startswith('enable'):
                print("COMMAND: enable")
                print("ACCOUNT: " + str(msg['from']))
                action = toggle_state(msg['from'].bare,
                                  True)
            elif message.lower().startswith('disable'):
                print("COMMAND: disable")
                print("ACCOUNT: " + str(msg['from']))
                action = toggle_state(msg['from'].bare,
                                  False)
            else:
                action = "Unknown command. Press \"help\" for list of commands"
            msg.reply(action).send()

    async def send_updates(self, event):
        #while not offline:
        while True:
            print(time.strftime("%H:%M:%S"))
            # print(offline)
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
                        # TODO check if jid online
                        # https://slixmpp.readthedocs.io/en/latest/api/plugins/xep_0199.html
                        # d = self.send_ping(self, jid)
                        # print('d')
                        # print(d)
                        new = await initdb(jid, False, get_unread)
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
            await asyncio.sleep(60 * 3)

    # asyncio.ensure_future(send_updates(self))

async def check_updates():
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
                jid = file[:-3]
                await initdb(
                       jid,
                       False,
                       download_updates
                )
        await asyncio.sleep(60 * 30)

asyncio.ensure_future(check_updates())

# async def tasks():
#     # Begin scanning feeds
#     task = asyncio.create_task(check_updates())
#     await task

async def tasks(jid, password):
    # Begin scanning feeds
    await asyncio.gather(
        check_updates(),
        Slixfeed(jid, password).send_updates()
    )

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
async def initdb(jid, message, callback):
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
        return await callback(conn, message)
    else:
        return await callback(conn)

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
        print(time.strftime("%H:%M:%S"), "conn.cursor() from create_table(conn, create_table_sql)")
        c.execute(create_table_sql)
    except Error as e:
        print(e)

# def setup_info(jid):
# def start_process(jid):
async def download_updates(conn):
    with conn:
        # cur = conn.cursor()
        # get current date
        #today = date.today()
        urls = await get_subscriptions(conn)
        for url in urls:
            #"".join(url)
            source = url[0]
            html = await download_page(url[0])
            print(url[0])
            if html:
                try:
                    feed = feedparser.parse(html)
                    if feed.bozo:
                        bozo = ("WARNING: Bozo detected for feed <{}>. "
                                "For more information, visit "
                                "https://pythonhosted.org/feedparser/bozo.html"
                                .format(source))
                        print(bozo)
                except (IncompleteReadError, IncompleteRead, error.URLError) as e:
                    print(e)
                    return
            # TODO Place these couple of lines back down
            # NOTE Need to correct the SQL statement to do so
            entries = feed.entries
            length = len(entries)
            await remove_entry(conn, source, length)
            for entry in entries:
                if entry.has_key("title"):
                    title = entry.title
                else:
                    title = feed["feed"]["title"]
                link = source if not entry.link else entry.link
                exist = await check_entry(conn, title, link)
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
                    await add_entry(conn, entry)
                    await set_date(conn, source)
                    #make_message
    #                 message = title + '\n\n' + summary + '\n\nLink: ' + link
    #                 print(message)
    #                 news.append(message)
    #                 print(len(news))
    # return news

async def download_page(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                html = await response.text()
                return html
            print("Status:", response.status)
            print("Content-type:", response.headers['content-type'])

loop = asyncio.get_event_loop()
loop.run_until_complete

async def check_feed(conn, url):
    """
    Check whether a feed exists
    Query for feeds by url
    :param conn:
    :param url:
    :return: row
    """
    cur = conn.cursor()
    print(time.strftime("%H:%M:%S"), "conn.cursor() from check_feed(conn, url)")
    sql = "SELECT id FROM feeds WHERE address = ?"
    cur.execute(sql, (url,))
    return cur.fetchone()

async def add_feed(conn, url):
    """
    Add a new feed into the feeds table
    :param conn:
    :param feed:
    :return: string
    """
    #conn = create_connection(db_file)
    cur = conn.cursor()
    print(time.strftime("%H:%M:%S"), "conn.cursor() from add_feed(conn, url)")
    exist = await check_feed(conn, url)
    if not exist:
        feed = feedparser.parse(url)
        if feed.bozo:
            bozo = ("WARNING: Bozo detected. Failed to load URL.")
            print(bozo)
            return "Failed to parse URL as feed"
        title = feedparser.parse(url)["feed"]["title"]
        feed = (title, url, 1)
        sql = """INSERT INTO feeds(name,address,status)
                 VALUES(?,?,?) """
        cur.execute(sql, feed)
        conn.commit()
        print(time.strftime("%H:%M:%S"), "conn.commit() from add_feed(conn, url)")
        # source = title if not '' else url
        source = title if title else '<' + url + '>'
        msg = """News source "{}" has been added to subscriptions list
              """.format(source)
    else:
        msg = "News source is already listed in the subscription list"
    return msg

async def remove_feed(conn, id):
    """
    Delete a feed by feed id
    :param conn:
    :param id: id of the feed
    :return: string
    """
    # You have chose to remove feed (title, url) from your feed list.
    # Enter "delete" to confirm removal.
    #conn = create_connection(db_file)
    cur = conn.cursor()
    print(time.strftime("%H:%M:%S"), "conn.cursor() from remove_feed(conn, id)")
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
    print(time.strftime("%H:%M:%S"), "conn.commit() from remove_feed(conn, id)")
    return """News source <{}> has been removed from subscriptions list
           """.format(url)

async def get_unread(conn):
    """
    Check read status of entry
    :param conn:
    :param id: id of the entry
    :return: string
    """
    with conn:
        entry = []
        cur = conn.cursor()
        print(time.strftime("%H:%M:%S"), "conn.cursor() from get_unread(conn)")
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
        entry = "{}\n\n{}\n\nLink to article:\n{}".format(entry[0], entry[1], entry[2])
        mark_as_read(conn, id)
        return entry

async def mark_as_read(conn, id):
    """
    Set read status of entry
    :param conn:
    :param id: id of the entry
    """
    cur = conn.cursor()
    print(time.strftime("%H:%M:%S"), "conn.cursor() from mark_as_read(conn, id)")
    sql = "UPDATE entries SET summary = '', read = 1 WHERE id = ?"
    cur.execute(sql, (id,))
    conn.commit()
    print(time.strftime("%H:%M:%S"), "conn.commit() from mark_as_read(conn, id)")
    #conn.close()

# TODO test
async def toggle_status(conn, id):
    """
    Set status of feed
    :param conn:
    :param id: id of the feed
    :return: string
    """
    #conn = create_connection(db_file)
    cur = conn.cursor()
    print(time.strftime("%H:%M:%S"), "conn.cursor() from toggle_status(conn, id)")
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
    print(time.strftime("%H:%M:%S"), "conn.commit() from toggle_status(conn, id)")
    return notice

async def toggle_state(jid, state):
    """
    Set status of update
    :param jid: jid of the user
    :param state: boolean
    :return:
    """
    db_dir = get_default_dbdir()
    os.chdir(db_dir)
    db_file = r"{}.db".format(jid)
    bk_file = r"{}.db.bak".format(jid)
    if state:
        if path.exists(db_file):
            return "Updates are already enabled"
        elif path.exists(bk_file):
            os.renames(bk_file, db_file)
            return "Updates are now enabled"
    else:
        if path.exists(bk_file):
            return "Updates are already disabled"
        elif path.exists(db_file):
            os.renames(db_file, bk_file)
            return "Updates are now disabled"
    
    # if path.exists(db_file):
    #     os.renames(db_file, db_file + ".bak")
    #     break
    # db_file = r"{}.db.bak".format(jid)
    # if path.exists(db_file):
    #     os.renames(db_file, jid,+".db")

async def set_date(conn, url):
    """
    Set last update date of feed
    :param url: url of the feed
    :return:
    """
    today = date.today()
    cur = conn.cursor()
    print(time.strftime("%H:%M:%S"), "conn.cursor() from set_date(conn, url)")
    sql = "UPDATE feeds SET updated = :today WHERE address = :url"
    cur.execute(sql, {"today": today, "url": url})
    conn.commit()
    print(time.strftime("%H:%M:%S"), "conn.commit() from set_date(conn, url)")

async def get_subscriptions(conn):
    """
    Query feeds
    :param conn:
    :return: rows (tuple)
    """
    cur = conn.cursor()
    print(time.strftime("%H:%M:%S"), "conn.cursor() from get_subscriptions(conn)")
    sql = "SELECT address FROM feeds WHERE status = 1"
    result = cur.execute(sql)
    return result

async def list_subscriptions(conn):
    """
    Query feeds
    :param conn:
    :return: rows (string)
    """
    cur = conn.cursor()
    print(time.strftime("%H:%M:%S"), "conn.cursor() from list_subscriptions(conn)")
    #sql = "SELECT id, address FROM feeds"
    sql = "SELECT name, address, updated, id, status FROM feeds"
    results = cur.execute(sql)
    feeds_list = "List of subscriptions: \n"
    counter = 0
    for result in results:
        counter += 1
        #feeds_list = feeds_list + '\n {}. {}'.format(str(result[0]), str(result[1]))
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

async def last_entries(conn, num):
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
    cur = conn.cursor()
    sql = "SELECT title, link FROM entries ORDER BY ROWID DESC LIMIT {}".format(num)
    results = cur.execute(sql)
    titles_list = "Recent {} titles: \n".format(num)
    for result in results:
        # titles_list += """\nTitle: {} \nLink: {}
        titles_list += """\n{} \n{}
        """.format(str(result[0]), str(result[1]))
    return titles_list

async def search_entries(conn, query):
    """
    Query feeds
    :param conn:
    :param query: string
    :return: rows (string)
    """
    if len(query) < 2:
        return "Please enter at least 2 characters to search"
    cur = conn.cursor()
    sql = "SELECT title, link FROM entries WHERE title LIKE '%{}%' LIMIT 50".format(query)
    # sql = "SELECT title, link FROM entries WHERE title OR link LIKE '%{}%'".format(query)
    results = cur.execute(sql)
    results_list = "Search results for '{}': \n".format(query)
    counter = 0
    for result in results:
        counter += 1
        # titles_list += """\nTitle: {} \nLink: {}
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
    print(time.strftime("%H:%M:%S"), "conn.cursor() from check_entry(conn, title, link)")
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
    print(time.strftime("%H:%M:%S"), "conn.cursor() from add_entry(conn, entry)")
    cur.execute(sql, entry)
    conn.commit()
    print(time.strftime("%H:%M:%S"), "conn.commit() from add_entry(conn, entry)")

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
    print(time.strftime("%H:%M:%S"), "conn.cursor() from remove_entry(conn, source, length)")
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
        print(time.strftime("%H:%M:%S"), "conn.commit() from remove_entry(conn, source, length)")

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
    xmpp.register_plugin('xep_0004') # Data Forms
    xmpp.register_plugin('xep_0030') # Service Discovery
    xmpp.register_plugin('xep_0045') # Multi-User Chat
    xmpp.register_plugin('xep_0060') # PubSub
    xmpp.register_plugin('xep_0199') # XMPP Ping

    # Connect to the XMPP server and start processing XMPP stanzas.
    xmpp.connect()
    xmpp.process()
