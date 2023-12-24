#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

FIXME

1) Check feed duplication on runtime.
    When feed is valid and is not yet in the database it is
    posible to send a batch which would result in duplication.
    Consequently, it might result in database lock error upon
    feed removal attempt

TODO

1) from slixfeed.FILENAME import XYZ
   See project /chaica/feed2toot

2) SQL prepared statements;

3) Machine Learning for scrapping Title, Link, Summary and Timstamp;
   Scrape element </article> (example: Liferea)
   http://intertwingly.net/blog/
   https://www.brandenburg.de/

4) Set MUC subject
   Feeds which entries are to be set as groupchat subject.
   Perhaps not, as it would require to check every feed for this setting.
   Maybe a separate bot;

5) Support categories;

6) XMPP commands;

7) Bot as transport;

8) OMEMO;

9) Logging;
   https://docs.python.org/3/howto/logging.html

10) Readability
    See project /buriy/python-readability

11) Download and upload/send article (xHTML, HTMLZ, Markdown, MHTML, TXT).

12) Fetch summary from URL, instead of storing summary, or
    Store 5 upcoming summaries.
    This would help making the database files smaller.

13) Support protocol Gopher
    See project /michael-lazar/pygopherd
    See project /gopherball/gb

14) Support ActivityPub @person@domain (see Tip Of The Day).

15) Tip Of The Day.
    Did you know that you can follow you favorite Mastodon feeds by just
    sending the URL address?
    Supported fediverse websites are:
        Akkoma, HubZilla, Mastodon, Misskey, Pixelfed, Pleroma, Soapbox.

16) Brand: News Broker, Newsman, Newsdealer, Laura Harbinger
    
17) See project /offpunk/offblocklist.py

18) Search messages of government regulated publishers, and promote other sources.
    Dear reader, we couldn't get news from XYZ as they don't provide RSS feeds.
    However, you might want to get news from (1) (2) and (3) instead!

"""

# vars and their meanings:
# jid = Jabber ID (XMPP)
# res = response (HTTP)

from argparse import ArgumentParser
import configparser
import filehandler
# from filehandler import get_default_confdir
from getpass import getpass
import logging
import os

# from datetime import date
# import time

# from eliot import start_action, to_file
# # to_file(open("slixfeed.log", "w"))
# # with start_action(action_type="set_date()", jid=jid):
# # with start_action(action_type="message()", msg=msg):

#import slixfeed.irchandler
from xmpphandler import Slixfeed
#import slixfeed.matrixhandler


if __name__ == '__main__':
    # Setup the command line arguments.
    parser = ArgumentParser(description=Slixfeed.__doc__)

    # Output verbosity options.
    parser.add_argument(
         "-q",
         "--quiet",
         help="set logging to ERROR",
         action="store_const",
         dest="loglevel",
         const=logging.ERROR,
         default=logging.INFO
         )
    parser.add_argument(
        "-d",
        "--debug",
        help="set logging to DEBUG",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.INFO
        )

    # JID and password options.
    parser.add_argument(
        "-j",
        "--jid",
        dest="jid",
        help="Jabber ID"
        )
    parser.add_argument(
        "-p",
        "--password",
        dest="password",
        help="Password of JID"
        )
    parser.add_argument(
        "-n",
        "--nickname",
        dest="nickname",
        help="Display name"
        )

    args = parser.parse_args()

    # Setup logging.
    logging.basicConfig(
        level=args.loglevel,
        format='%(levelname)-8s %(message)s'
        )

    # Try configuration file
    config = configparser.RawConfigParser()
    config_dir = filehandler.get_default_confdir()
    if not os.path.isdir(config_dir):
        os.mkdir(config_dir)
    # TODO Copy file from /etc/slixfeed/ or /usr/share/slixfeed/
    config_file = os.path.join(config_dir, r"accounts.ini")
    config.read(config_file)
    if config.has_section("XMPP"):
        xmpp = config["XMPP"]
        nickname = xmpp["nickname"]
        username = xmpp["username"]
        password = xmpp["password"]

    # Use arguments if were given
    if args.jid:
        username = args.jid
    if args.password:
        password = args.password
    if args.nickname:
        nickname = args.nickname

    # Prompt for credentials if none were given
    if username is None:
        username = input("Username: ")
    if password is None:
        password = getpass("Password: ")
    if nickname is None:
        nickname = input("Nickname: ")

    # Setup the Slixfeed and register plugins. Note that while plugins may
    # have interdependencies, the order in which you register them does
    # not matter.
    xmpp = Slixfeed(username, password, nickname)
    xmpp.register_plugin('xep_0004') # Data Forms
    xmpp.register_plugin('xep_0030') # Service Discovery
    xmpp.register_plugin('xep_0045') # Multi-User Chat
    xmpp.register_plugin('xep_0048') # Bookmarks
    xmpp.register_plugin('xep_0060') # PubSub
    xmpp.register_plugin('xep_0199', {'keepalive': True, 'frequency': 15}) # XMPP Ping
    xmpp.register_plugin('xep_0249') # Multi-User Chat
    xmpp.register_plugin('xep_0402') # PEP Native Bookmarks

    # Connect to the XMPP server and start processing XMPP stanzas.
    xmpp.connect()
    xmpp.process()
