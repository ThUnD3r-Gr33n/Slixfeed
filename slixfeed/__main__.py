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
    xmpp.register_plugin('xep_0060') # PubSub
    xmpp.register_plugin('xep_0199') # XMPP Ping

    # Connect to the XMPP server and start processing XMPP stanzas.
    xmpp.connect()
    xmpp.process()
