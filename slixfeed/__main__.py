"""

FIXME

1) Check feed duplication on runtime.
    When feed is valid and is not yet in the database it is
    posible to send a batch which would result in duplication.
    Consequently, it might result in database lock error upon
    feed removal attempt

2) Communicate to messages of new contacts (not subscribed and not in roster)

TODO

2) Machine Learning for scrapping Title, Link, Summary and Timstamp;
   Scrape element </article> (example: Liferea)
   http://intertwingly.net/blog/
   https://www.brandenburg.de/

3) Set MUC subject
   Feeds which entries are to be set as groupchat subject.
   Perhaps not, as it would require to check every feed for this setting.
   Maybe a separate bot;

5) OMEMO;

6) Logging;
   https://docs.python.org/3/howto/logging.html

9.1) IDEA: Bot to display Title and Excerpt
     (including sending a PDF version of it) of posted link

10) Fetch summary from URL, instead of storing summary, or
    Store 5 upcoming summaries.
    This would help making the database files smaller.

13) Tip Of The Day.
    Did you know that you can follow you favorite Mastodon feeds by just
    sending the URL address?
    Supported fediverse websites are:
        Akkoma, Firefish (Calckey), Friendica, HubZilla,
        Mastodon, Misskey, Pixelfed, Pleroma, Socialhome, Soapbox.

14) Brand: News Broker, Newsman, Newsdealer, Laura Harbinger

16) Search messages of government regulated publishers, and promote other sources.
    Dear reader, we couldn't get news from XYZ as they don't provide RSS feeds.
    However, you might want to get news from (1) (2) and (3) instead!

17) The operator account will be given reports from the bot about its
    activities every X minutes.
    When a suspicious activity is detected, it will be reported immediately.

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
# # to_file(open('slixfeed.log', 'w'))
# # with start_action(action_type='set_date()', jid=jid):
# # with start_action(action_type='message()', msg=msg):

#import slixfeed.smtp
#import slixfeed.irc
#import slixfeed.matrix

import slixfeed.config as config
from slixfeed.version import __version__

import socks
import socket

xmpp_type = config.get_value('accounts', 'XMPP', 'type')

if not xmpp_type:
    raise Exception('Key type is missing from accounts.ini.')

match xmpp_type:
    case 'client':
        from slixfeed.xmpp.client import Slixfeed
    case 'component':
        from slixfeed.xmpp.component import SlixfeedComponent


class JabberComponent:
    def __init__(self, jid, secret, hostname, port, alias=None):
        xmpp = SlixfeedComponent(jid, secret, hostname, port, alias)
        xmpp.register_plugin('xep_0004') # Data Forms
        xmpp.register_plugin('xep_0030') # Service Discovery
        xmpp.register_plugin('xep_0045') # Multi-User Chat
        # xmpp.register_plugin('xep_0048') # Bookmarks
        xmpp.register_plugin('xep_0050') # Ad-Hoc Commands
        xmpp.register_plugin('xep_0054') # vcard-temp
        xmpp.register_plugin('xep_0060') # Publish-Subscribe
        # xmpp.register_plugin('xep_0065') # SOCKS5 Bytestreams
        xmpp.register_plugin('xep_0066') # Out of Band Data
        xmpp.register_plugin('xep_0071') # XHTML-IM
        xmpp.register_plugin('xep_0084') # User Avatar
        xmpp.register_plugin('xep_0085') # Chat State Notifications
        xmpp.register_plugin('xep_0115') # Entity Capabilities
        xmpp.register_plugin('xep_0122') # Data Forms Validation
        xmpp.register_plugin('xep_0153') # vCard-Based Avatars
        xmpp.register_plugin('xep_0199', {'keepalive': True}) # XMPP Ping
        xmpp.register_plugin('xep_0203') # Delayed Delivery
        xmpp.register_plugin('xep_0249') # Direct MUC Invitations
        xmpp.register_plugin('xep_0297') # Stanza Forwarding
        xmpp.register_plugin('xep_0356') # Privileged Entity
        xmpp.register_plugin('xep_0363') # HTTP File Upload
        xmpp.register_plugin('xep_0402') # PEP Native Bookmarks
        xmpp.register_plugin('xep_0444') # Message Reactions
        xmpp.connect()
        xmpp.process()


class JabberClient:
    def __init__(self, jid, password, hostname=None, port=None, alias=None):
        xmpp = Slixfeed(jid, password, hostname, port, alias)
        xmpp.register_plugin('xep_0004') # Data Forms
        xmpp.register_plugin('xep_0030') # Service Discovery
        xmpp.register_plugin('xep_0045') # Multi-User Chat
        xmpp.register_plugin('xep_0048') # Bookmarks
        xmpp.register_plugin('xep_0050') # Ad-Hoc Commands
        xmpp.register_plugin('xep_0054') # vcard-temp
        xmpp.register_plugin('xep_0060') # Publish-Subscribe
        # xmpp.register_plugin('xep_0065') # SOCKS5 Bytestreams
        xmpp.register_plugin('xep_0066') # Out of Band Data
        xmpp.register_plugin('xep_0071') # XHTML-IM
        xmpp.register_plugin('xep_0084') # User Avatar
        xmpp.register_plugin('xep_0085') # Chat State Notifications
        xmpp.register_plugin('xep_0115') # Entity Capabilities
        xmpp.register_plugin('xep_0122') # Data Forms Validation
        xmpp.register_plugin('xep_0153') # vCard-Based Avatars
        xmpp.register_plugin('xep_0199', {'keepalive': True}) # XMPP Ping
        xmpp.register_plugin('xep_0249') # Direct MUC Invitations
        xmpp.register_plugin('xep_0363') # HTTP File Upload
        xmpp.register_plugin('xep_0402') # PEP Native Bookmarks
        xmpp.register_plugin('xep_0444') # Message Reactions

        # proxy_enabled = config.get_value('accounts', 'XMPP', 'proxy_enabled')
        # if proxy_enabled == '1':
        #     values = config.get_value('accounts', 'XMPP', [
        #         'proxy_host',
        #         'proxy_port',
        #         'proxy_username',
        #         'proxy_password'
        #         ])
        #     print('Proxy is enabled: {}:{}'.format(values[0], values[1]))
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

        address = config.get_value('accounts', 'XMPP Client',
                                   ['hostname', 'port'])
        if address[0] and address[1]:
            xmpp.connect(tuple(address))
        else:
            xmpp.connect()
        xmpp.process()


def main():

    config_dir = config.get_default_config_directory()
    logging.info('Reading configuration from {}'.format(config_dir))
    print('Reading configuration from {}'.format(config_dir))

    # values = config.get_value('accounts', 'XMPP Proxy',
    #                           ['socks5_host', 'socks5_port'])
    # if values[0] and values[1]:
    #     host = values[0]
    #     port = values[1]
    #     s = socks.socksocket()
    #     s.set_proxy(socks.SOCKS5, host, port)
    #     # socks.set_default_proxy(socks.SOCKS5, host, port)
    #     # socket.socket = socks.socksocket

    # Setup the command line arguments.
    match xmpp_type:
        case 'client':
            parser = ArgumentParser(description=Slixfeed.__doc__)
        case 'component':
            parser = ArgumentParser(description=SlixfeedComponent.__doc__)

    parser.add_argument('-v', '--version', help='Print version',
                        action='version', version=__version__)

    # Output verbosity options.
    parser.add_argument('-q', '--quiet', help='set logging to ERROR',
                        action='store_const', dest='loglevel',
                        const=logging.ERROR, default=logging.INFO)
    parser.add_argument('-d', '--debug', help='set logging to DEBUG',
                        action='store_const', dest='loglevel',
                        const=logging.DEBUG, default=logging.INFO)

    # JID and password options.
    parser.add_argument('-j', '--jid', help='Jabber ID', dest='jid')
    parser.add_argument('-p', '--password', help='Password of JID',
                        dest='password')
    parser.add_argument('-a', '--alias', help='Display name', dest='alias')
    parser.add_argument('-n', '--hostname', help='Hostname', dest='hostname')
    parser.add_argument('-o', '--port', help='Port number', dest='port')

    args = parser.parse_args()

    # Setup logging.
    logging.basicConfig(level=args.loglevel,
                        format='%(levelname)-8s %(message)s')

    # Try configuration file
    values = config.get_value('accounts', 'XMPP Client',
                              ['alias', 'jid', 'password', 'hostname', 'port'])
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
        jid = input('JID: ')
    if not password:
        password = getpass('Password: ')
    if not alias:
        alias = (input('Alias: ')) or 'Slixfeed'

    match xmpp_type:
        case 'client':
            JabberClient(jid, password, hostname=hostname, port=port, alias=alias)
        case 'component':
            JabberComponent(jid, password, hostname, port, alias=alias)
    sys.exit(0)

if __name__ == '__main__':
    main()
