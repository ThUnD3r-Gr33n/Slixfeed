"""

FIXME

1) Check feed duplication on runtime.
    When feed is valid and is not yet in the database it is
    posible to send a batch which would result in duplication.
    Consequently, it might result in database lock error upon
    feed removal attempt

TODO

1) SQL prepared statements;

2) Machine Learning for scrapping Title, Link, Summary and Timstamp;
   Scrape element </article> (example: Liferea)
   http://intertwingly.net/blog/
   https://www.brandenburg.de/

3) Set MUC subject
   Feeds which entries are to be set as groupchat subject.
   Perhaps not, as it would require to check every feed for this setting.
   Maybe a separate bot;

4) Support categories;

5) XMPP commands;

6) Bot as service;

7) OMEMO;

8) Logging;
   https://docs.python.org/3/howto/logging.html

9) Readability
    See project /buriy/python-readability

9.1) IDEA: Bot to display Title and Excerpt
     (including sending a PDF version of it) of posted link

10) Fetch summary from URL, instead of storing summary, or
    Store 5 upcoming summaries.
    This would help making the database files smaller.

11) Support protocol Gopher
    See project /michael-lazar/pygopherd
    See project /gopherball/gb

12) Support ActivityPub @person@domain (see Tip Of The Day).

13) Tip Of The Day.
    Did you know that you can follow you favorite Mastodon feeds by just
    sending the URL address?
    Supported fediverse websites are:
        Akkoma, Firefish (Calckey), Friendica, HubZilla,
        Mastodon, Misskey, Pixelfed, Pleroma, Socialhome, Soapbox.

14) Brand: News Broker, Newsman, Newsdealer, Laura Harbinger
    
15) See project /offpunk/offblocklist.py

16) Search messages of government regulated publishers, and promote other sources.
    Dear reader, we couldn't get news from XYZ as they don't provide RSS feeds.
    However, you might want to get news from (1) (2) and (3) instead!

17) Make the program portable (directly use the directory assets) -- Thorsten

18) The operator account will be given reports from the bot about its
    activities every X minutes.
    When a suspicious activity is detected, it will be reported immediately.

19) Communicate to messages of new contacts (not subscribed and not in roster)

"""

# vars and their meanings:
# jid = Jabber ID (XMPP)
# res = response (HTTP)

from argparse import ArgumentParser
from getpass import getpass
import sys
import configparser
# import filehandler
# from slixfeed.file import get_default_confdir
from getpass import getpass
import logging
import os

# from datetime import date
# import time

# from eliot import start_action, to_file
# # to_file(open("slixfeed.log", "w"))
# # with start_action(action_type="set_date()", jid=jid):
# # with start_action(action_type="message()", msg=msg):

#import slixfeed.smtp
#import slixfeed.irc
#import slixfeed.matrix

from slixfeed.config import get_value

import socks
import socket

xmpp_type = get_value(
            "accounts", "XMPP", "type")

match xmpp_type:
    case "client":
        from slixfeed.xmpp.client import Slixfeed
    case "component":
        from slixfeed.xmpp.component import Slixfeed


class JabberComponent:
    def __init__(self, jid, secret, hostname, port, alias):
        xmpp = Slixfeed(jid, secret, hostname, port, alias)
        xmpp.register_plugin('xep_0004') # Data Forms
        xmpp.register_plugin('xep_0030') # Service Discovery
        xmpp.register_plugin('xep_0045') # Multi-User Chat
        # xmpp.register_plugin('xep_0048') # Bookmarks
        xmpp.register_plugin('xep_0054') # vcard-temp
        xmpp.register_plugin('xep_0060') # Publish-Subscribe
        # xmpp.register_plugin('xep_0065') # SOCKS5 Bytestreams
        xmpp.register_plugin('xep_0066') # Out of Band Data
        xmpp.register_plugin('xep_0071') # XHTML-IM
        xmpp.register_plugin('xep_0084') # User Avatar
        # xmpp.register_plugin('xep_0085') # Chat State Notifications
        xmpp.register_plugin('xep_0153') # vCard-Based Avatars
        xmpp.register_plugin('xep_0199', {'keepalive': True}) # XMPP Ping
        xmpp.register_plugin('xep_0249') # Multi-User Chat
        xmpp.register_plugin('xep_0363') # HTTP File Upload
        xmpp.register_plugin('xep_0402') # PEP Native Bookmarks
        xmpp.connect()
        xmpp.process()


class JabberClient:
    def __init__(self, jid, password, alias):
        # Setup the Slixfeed and register plugins. Note that while plugins may
        # have interdependencies, the order in which you register them does
        # not matter.
        xmpp = Slixfeed(jid, password, alias)
        xmpp.register_plugin('xep_0004') # Data Forms
        xmpp.register_plugin('xep_0030') # Service Discovery
        xmpp.register_plugin('xep_0045') # Multi-User Chat
        xmpp.register_plugin('xep_0048') # Bookmarks
        xmpp.register_plugin('xep_0054') # vcard-temp
        xmpp.register_plugin('xep_0060') # Publish-Subscribe
        # xmpp.register_plugin('xep_0065') # SOCKS5 Bytestreams
        xmpp.register_plugin('xep_0066') # Out of Band Data
        xmpp.register_plugin('xep_0071') # XHTML-IM
        xmpp.register_plugin('xep_0084') # User Avatar
        # xmpp.register_plugin('xep_0085') # Chat State Notifications
        xmpp.register_plugin('xep_0153') # vCard-Based Avatars
        xmpp.register_plugin('xep_0199', {'keepalive': True}) # XMPP Ping
        xmpp.register_plugin('xep_0249') # Multi-User Chat
        xmpp.register_plugin('xep_0363') # HTTP File Upload
        xmpp.register_plugin('xep_0402') # PEP Native Bookmarks

        # proxy_enabled = get_value("accounts", "XMPP", "proxy_enabled")
        # if proxy_enabled == '1':
        #     values = get_value("accounts", "XMPP", [
        #         "proxy_host",
        #         "proxy_port",
        #         "proxy_username",
        #         "proxy_password"
        #         ])
        #     print("Proxy is enabled: {}:{}".format(values[0], values[1]))
        #     xmpp.use_proxy = True
        #     xmpp.proxy_config = {
        #         'host': values[0],
        #         'port': values[1],
        #         'username': values[2],
        #         'password': values[3]
        #     }
        #     proxy = {'socks5': (values[0], values[1])}
        #     xmpp.proxy = {'socks5': ('localhost', 9050)}

        # Connect to the XMPP server and start processing XMPP stanzas.

        address = get_value(
            "accounts", "XMPP Client", ["hostname", "port"])
        if address[0] and address[1]:
            xmpp.connect(tuple(address))
        else:
            xmpp.connect()
        xmpp.process()


def main():

    values = get_value(
        "accounts", "XMPP Proxy", ["socks5_host", "socks5_port"])
    if values[0] and values[1]:
        host = values[0]
        port = values[1]
        s = socks.socksocket()
        s.set_proxy(socks.SOCKS5, host, port)
        # socks.set_default_proxy(socks.SOCKS5, host, port)
        # socket.socket = socks.socksocket

    # Setup the command line arguments.
    parser = ArgumentParser(description=Slixfeed.__doc__)

    # Output verbosity options.
    parser.add_argument(
        "-q", "--quiet", help="set logging to ERROR",
        action="store_const", dest="loglevel",
        const=logging.ERROR, default=logging.INFO)
    parser.add_argument(
        "-d", "--debug", help="set logging to DEBUG",
        action="store_const", dest="loglevel",
        const=logging.DEBUG, default=logging.INFO)

    # JID and password options.
    parser.add_argument(
        "-j", "--jid", dest="jid", help="Jabber ID")
    parser.add_argument(
        "-p", "--password", dest="password", help="Password of JID")
    parser.add_argument(
        "-a", "--alias", dest="alias", help="Display name")
    parser.add_argument(
        "-n", "--hostname", dest="hostname", help="Hostname")
    parser.add_argument(
        "-o", "--port", dest="port", help="Port number")

    args = parser.parse_args()

    # Setup logging.
    logging.basicConfig(
        level=args.loglevel, format='%(levelname)-8s %(message)s')

    # Try configuration file
    values = get_value(
        "accounts", "XMPP Client", [
            "alias", "jid", "password", "hostname", "port"])
    alias = values[0]
    jid = values[1]
    password = values[2]
    hostname = values[3]
    port = values[4]

    # Use arguments if were given
    if args.jid:
        jid = args.jid
    if args.password:
        password = args.password
    if args.alias:
        alias = args.alias
    if args.hostname:
        hostname = args.hostname
    if args.port:
        port = args.port

    # Prompt for credentials if none were given
    if not jid:
        jid = input("JID: ")
    if not password:
        password = getpass("Password: ")
    if not alias:
        alias = (input("Alias: ")) or "Slixfeed"

    match xmpp_type:
        case "client":
            JabberClient(jid, password, alias)
        case "component":
            JabberComponent(jid, password, hostname, port, alias)
    sys.exit(0)

if __name__ == "__main__":
    main()
