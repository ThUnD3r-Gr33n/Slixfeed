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
import feedparser
import slixmpp

from eliot import start_action, to_file

from . import database

to_file(open("slixfeed.log", "w"))


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
        # print("start")
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
        # print("message")
        # time.sleep(1)
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
        with start_action(action_type="message()", msg=msg):
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
                    action = await initdb(msg['from'].bare, database.last_entries, message[12:])
                elif message.lower().startswith('feed search '):
                    print("COMMAND: feed search")
                    print("ACCOUNT: " + str(msg['from']))
                    action = await initdb( msg['from'].bare, database.search_entries, message[12:])
                elif message.lower().startswith('feed list'):
                    print("COMMAND: feed list")
                    print("ACCOUNT: " + str(msg['from']))
                    action = await initdb(msg['from'].bare, database.list_subscriptions)
                elif message.lower().startswith('feed add '):
                    print("COMMAND: feed add")
                    print("ACCOUNT: " + str(msg['from']))
                    action = await initdb(msg['from'].bare, is_feed_exist, message[9:])
                elif message.lower().startswith('feed remove '):
                    print("COMMAND: feed remove")
                    print("ACCOUNT: " + str(msg['from']))
                    action = await initdb(msg['from'].bare, database.remove_feed, message[12:])
                elif message.lower().startswith('feed status '):
                    print("COMMAND: feed status")
                    print("ACCOUNT: " + str(msg['from']))
                    action = await initdb(msg['from'].bare, database.toggle_status, message[12:])
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
        # print("check_updates")
        # time.sleep(1)
        with start_action(action_type="check_updates()", event=event):
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
        # print("send_updates")
        # time.sleep(1)
        with start_action(action_type="send_updates()", event=event):
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
                                database.get_unread
                            )
                            if new:
                                msg = self.make_message(
                                    mto=jid,
                                    mbody=new,
                                    mtype='chat'
                                )
                                msg.send()
                await asyncio.sleep(15)


def print_help():
    # print("print_help")
    # time.sleep(1)
    msg = ("Slixfeed - News syndication bot for Jabber/XMPP \n"
           "\n"
           "DESCRIPTION: \n"
           " Slixfeed is a news aggregator bot for online news feeds. \n"
           "\n"
           "BASIC USAGE: \n"
           " enable \n"
           "   Send updates. \n"
           " disable \n"
           "   Stop sending updates. \n"
           " feed list \n"
           "   List subscriptions. \n"
           "\n"
           "EDIT OPTIONS: \n"
           " feed add URL \n"
           "   Add URL to subscription list. \n"
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


# Function from buku
# https://github.com/jarun/buku
# Arun Prakash Jana (jarun)
# Dmitry Marakasov (AMDmi3)
def get_default_dbdir():
    # print("get_default_dbdir")
    # time.sleep(1)
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
    # print("initdb")
    # time.sleep(1)
    with start_action(action_type="initdb()", jid=jid):
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
    # print("download_updates")
    # print("db_file")
    # print(db_file)
    # time.sleep(1)
    with start_action(action_type="download_updates()", db=db_file):
        urls = await database.get_subscriptions(db_file)

    for url in urls:
        with start_action(action_type="download_updates()", url=url):
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
                length = len(entries)
                await database.remove_entry(db_file, source, length)
    
                for entry in entries:
                    if entry.has_key("title"):
                        title = entry.title
                    else:
                        title = feed["feed"]["title"]
                    link = source if not entry.link else entry.link
                    exist = await database.check_entry(db_file, title, link)
        
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
                        await database.add_entry_and_set_date(db_file, source, entry)


async def download_feed(url):
    with start_action(action_type="download_feed()", url=url):
    # print("download_feed")
        # time.sleep(1)
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession() as session:
    #    async with aiohttp.ClientSession(trust_env=True) as session:
            try:
                async with session.get(url, timeout=timeout) as response:
                    status = response.status
                    if response.status == 200:
                        doc = await response.text()
                        return [doc, status]
                    else:
                        return [False, status]
            except aiohttp.ClientError as e:
                print('Error', str(e))
                return [False, "error"]
            except asyncio.TimeoutError as e:
                print('Timeout', str(e))
                return [False, "timeout"]


async def is_feed_exist(db_file, url):
    # print("add_feed")
    # print("db_file")
    # print(db_file)
    # time.sleep(1)
    """
    Check whether feed exist, otherwise process it
    :param db_file:
    :param url:
    :return: string
    """
    exist = await database.check_feed(db_file, url)
    
    if not exist:
        res = await download_feed(url)
        await database.add_feed(db_file, url, res)
    else:
        return "News source is already listed in the subscription list"


def toggle_state(jid, state):
    # print("toggle_state")
    # time.sleep(1)
    """
    Set status of update
    :param jid: jid of the user
    :param state: boolean
    :return:
    """
    with start_action(action_type="set_date()", jid=jid):
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
