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

1) SQL prepared statements.

2) Machine Learning for scrapping Title, Link, Summary and Timstamp.

3) Support MUC.

4) Support categories.

5) Default prepackaged list of feeds.

6) XMPP commands.

7) Bot as transport.

8) OMEMO.

9) Logging.

10) Default feeds (e.g. Blacklisted News, TBOT etc.)

11) Download and upload/send article (xHTML, xHTMLZ, Markdown, MHTML, TXT).
    Use Readability.

12) Fetch summary from URL, instead of storing summary.

13) Support protocol Gopher
    https://github.com/michael-lazar/pygopherd
    https://github.com/gopherball/gb

13) Support ActivityPub @person@domain (see Tip Of The Day).

12) Tip Of The Day.
    Did you know that you can follow you favorite Mastodon feeds by just
    sending the URL address?
    Supported fediverse websites are:
        Akkoma, HubZilla, Mastodon, Misskey, Pixelfed, Pleroma, Soapbox.

"""

# vars and their meanings:
# jid = Jabber ID (XMPP)
# res = response (HTTP)

from argparse import ArgumentParser
from getpass import getpass
import logging

from datetime import date
import time

# from eliot import start_action, to_file
# # to_file(open("slixfeed.log", "w"))
# # with start_action(action_type="set_date()", jid=jid):
# # with start_action(action_type="message()", msg=msg):

#import irchandler
import xmpphandler
#import matrixhandler


if __name__ == '__main__':
    # Setup the command line arguments.
    parser = ArgumentParser(description=xmpphandler.Slixfeed.__doc__)

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
    xmpp = xmpphandler.Slixfeed(args.jid, args.password)
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
