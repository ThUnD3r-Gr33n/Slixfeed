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

# import socks
# import socket

account_xmpp = config.get_values('accounts.toml', 'xmpp')

# account = ConfigAccount() # TODO ~Delete~ Clear as soon as posible after is no longer needed

def main():

    config_dir = config.get_default_config_directory()
    logging.info('Reading configuration from {}'.format(config_dir))
    print('Reading configuration from {}'.format(config_dir))
    network_settings = config.get_values('settings.toml', 'network')
    print('User agent:', network_settings['user_agent'] or 'Slixfeed/0.1')
    if network_settings['http_proxy']: print('HTTP Proxy:', network_settings['http_proxy'])

    # values = config.get_value('accounts', 'XMPP Proxy',
    #                           ['socks5_host', 'socks5_port'])
    # if values[0] and values[1]:
    #     host = values[0]
    #     port = values[1]
    #     s = socks.socksocket()
    #     s.set_proxy(socks.SOCKS5, host, port)
    #     # socks.set_default_proxy(socks.SOCKS5, host, port)
    #     # socket.socket = socks.socksocket

    #parser = ArgumentParser(description=Slixfeed.__doc__)
    parser = ArgumentParser(description='Slixfeed News Bot')

    # Setup the command line arguments.
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

    # # Setup logging.
    # logging.basicConfig(level=args.loglevel,
    #                     format='%(levelname)-8s %(message)s')
    # # logging.basicConfig(format='[%(levelname)s] %(message)s')
    # logger = logging.getLogger()
    # logdbg = logger.debug
    # logerr = logger.error
    # lognfo = logger.info
    # logwrn = logger.warning

    # NOTE Temporarily archived
    # NOTE Consider removal of arguments jid, password and alias

    # # Try configuration file
    # jid = account[account_mode]['jid']
    # password = account[account_mode]['password']
    # alias = account[account_mode]['alias'] if 'alias' in account[account_mode] else None
    # hostname = account[account_mode]['hostname'] if 'hostname' in account[account_mode] else None
    # port = account[account_mode]['port'] if 'port' in account[account_mode] else None

    # # Use arguments if were given
    # if args.jid:
    #     jid = args.jid
    # if args.password:
    #     password = args.password
    # if args.alias:
    #     alias = args.alias
    # if args.hostname:
    #     hostname = args.hostname
    # if args.port:
    #     port = args.port

    # # Prompt for credentials if none were given
    # if not jid:
    #     jid = input('JID: ')
    # if not password:
    #     password = getpass('Password: ')
    # if not alias:
    #     alias = (input('Alias: ')) or 'Slixfeed'

    # Try configuration file
    if 'client' in account_xmpp:
        from slixfeed.xmpp.client import XmppClient
        jid = account_xmpp['client']['jid']
        password = account_xmpp['client']['password']
        alias = account_xmpp['client']['alias'] if 'alias' in account_xmpp['client'] else None
        hostname = account_xmpp['client']['hostname'] if 'hostname' in account_xmpp['client'] else None
        port = account_xmpp['client']['port'] if 'port' in account_xmpp['client'] else None
        XmppClient(jid, password, hostname, port, alias)
        # xmpp_client = Slixfeed(jid, password, hostname, port, alias)
        # xmpp_client.connect((hostname, port)) if hostname and port else xmpp_client.connect()
        # xmpp_client.process()

    if 'component' in account_xmpp:
        from slixfeed.xmpp.component import XmppComponent
        jid = account_xmpp['component']['jid']
        secret = account_xmpp['component']['password']
        alias = account_xmpp['component']['alias'] if 'alias' in account_xmpp['component'] else None
        hostname = account_xmpp['component']['hostname'] if 'hostname' in account_xmpp['component'] else None
        port = account_xmpp['component']['port'] if 'port' in account_xmpp['component'] else None
        XmppComponent(jid, secret, hostname, port, alias)
        # xmpp_component = SlixfeedComponent(jid, secret, hostname, port, alias)
        # xmpp_component.connect()
        # xmpp_component.process()

    sys.exit(0)

if __name__ == '__main__':
    main()
