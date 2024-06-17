#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

TODO

1) Function scan at "for entry in entries"
   Suppress directly calling function "add_entry" (accept db_file)
   Pass a list of valid entries to a new function "add_entries"
   (accept db_file) which would call function "add_entry" (accept cur).
   * accelerate adding of large set of entries at once.
   * prevent (or mitigate halt of consequent actions).
   * reduce I/O.

2) Call sqlite function from function statistics.
   Returning a list of values doesn't' seem to be a good practice.

3) Special statistics for operator:
   * Size of database(s);
   * Amount of JIDs subscribed;
   * Amount of feeds of all JIDs;
   * Amount of entries of all JIDs.

4) Consider to append text to remind to share presence
    '✒️ Share online status to receive updates'

5) Request for subscription
   if (await XmppUtilities.get_chat_type(self, jid_bare) == 'chat' and
       not self.client_roster[jid_bare]['to']):
       XmppPresence.subscription(self, jid_bare, 'subscribe')
       await XmppRoster.add(self, jid_bare)
       status_message = '✒️ Share online status to receive updates'
       XmppPresence.send(self, jid_bare, status_message)
       message_subject = 'RSS News Bot'
       message_body = 'Share online status to receive updates.'
       XmppMessage.send_headline(self, jid_bare, message_subject,
                                 message_body, 'chat')

"""

from datetime import datetime
from dateutil.parser import parse
from email.utils import parseaddr, parsedate, parsedate_to_datetime
import hashlib
from lxml import etree, html
import os
import random
import slixfeed.config as config
import slixfeed.dt as dt
import slixfeed.fetch as fetch
from slixfeed.log import Logger
import sys
from urllib.parse import (
    parse_qs,
    urlencode,
    urljoin,
    # urlparse,
    urlsplit,
    urlunsplit
    )

try:
    import tomllib
except:
    import tomli as tomllib

logger = Logger(__name__)


class DateAndTime:

#https://feedparser.readthedocs.io/en/latest/date-parsing.html

    def now():
        """
        ISO 8601 Timestamp.

        Returns
        -------
        date : ???
            ISO 8601 Timestamp.
        """
        date = datetime.now().isoformat()
        return date


    def convert_struct_time_to_iso8601(struct_time):
        date = datetime(*struct_time[:6])
        date = date.isoformat()
        return date


    def current_date():
        """
        Print MM DD, YYYY (Weekday Time) timestamp.

        Returns
        -------
        date : str
            MM DD, YYYY (Weekday Time) timestamp.
        """
        now = datetime.now()
        time = now.strftime("%B %d, %Y (%A %T)")
        return time


    def current_time():
        """
        Print HH:MM:SS timestamp.

        Returns
        -------
        date : str
            HH:MM:SS timestamp.
        """
        now = datetime.now()
        time = now.strftime("%H:%M:%S")
        return time


    def timestamp():
        """
        Print time stamp to be used in filename.

        Returns
        -------
        formatted_time : str
            %Y%m%d-%H%M%S timestamp.
        """
        now = datetime.now()
        formatted_time = now.strftime("%Y%m%d-%H%M%S")
        return formatted_time


    def validate(date):
        """
        Validate date format.

        Parameters
        ----------
        date : str
            Timestamp.

        Returns
        -------
        date : str
            Timestamp.
        """
        try:
            parse(date)
        except:
            date = DateAndTime.now()
        return date


    def rfc2822_to_iso8601(date):
        """
        Convert RFC 2822 into ISO 8601.

        Parameters
        ----------
        date : str
            RFC 2822 Timestamp.

        Returns
        -------
        date : str
            ISO 8601 Timestamp.
        """
        if parsedate(date):
            try:
                date = parsedate_to_datetime(date)
                date = date.isoformat()
            except:
                date = DateAndTime.now()
        return date


class Documentation:


    def manual(filename, section=None, command=None):
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: filename: {}'.format(function_name, filename))
        config_dir = config.get_default_config_directory()
        with open(config_dir + '/' + filename, mode="rb") as commands:
            cmds = tomllib.load(commands)
        if section == 'all':
            cmd_list = ''
            for cmd in cmds:
                for i in cmds[cmd]:
                    cmd_list += cmds[cmd][i] + '\n'
        elif command and section:
            try:
                cmd_list = cmds[section][command]
            except KeyError as e:
                logger.error(e)
                cmd_list = None
        elif section:
            try:
                cmd_list = []
                for cmd in cmds[section]:
                    cmd_list.extend([cmd])
            except KeyError as e:
                logger.error('KeyError:' + str(e))
                cmd_list = None
        else:
            cmd_list = []
            for cmd in cmds:
                cmd_list.extend([cmd])
        return cmd_list


class Html:


    async def extract_image_from_html(url):
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: url: {}'.format(function_name, url))
        result = await fetch.http(url)
        if not result['error']:
            data = result['content']
            tree = html.fromstring(data)
            # TODO Exclude banners, class="share" links etc.
            images = tree.xpath(
                '//img[not('
                    'contains(@src, "avatar") or '
                    'contains(@src, "cc-by-sa") or '
                    'contains(@src, "emoji") or '
                    'contains(@src, "icon") or '
                    'contains(@src, "logo") or '
                    'contains(@src, "letture") or '
                    'contains(@src, "poweredby_mediawi") or '
                    'contains(@src, "search") or '
                    'contains(@src, "share") or '
                    'contains(@src, "smiley")'
                ')]/@src')
            if len(images):
                image = images[0]
                image = str(image)
                image_url = Url.complete_url(url, image)
                return image_url


    def remove_html_tags(data):
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}'.format(function_name))
        parser = etree.HTMLParser()
        tree = etree.fromstring(data, parser)
        data = etree.tostring(tree, encoding='unicode', method='text')
        data = data.replace("\n\n", "\n")
        return data


    # /questions/9662346/python-code-to-remove-html-tags-from-a-string
    def _remove_html_tags(text):
        import xml.etree.ElementTree
        return ''.join(xml.etree.ElementTree.fromstring(text).itertext())


    def __remove_html_tags(data):
        from bs4 import BeautifulSoup
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}'.format(function_name))
        data = BeautifulSoup(data, "lxml").text
        data = data.replace("\n\n", "\n")
        return data


class MD:


    def export_to_markdown(jid, filename, results):
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid: {} filename: {}'
                    .format(function_name, jid, filename))
        with open(filename, 'w') as file:
            file.write('# Subscriptions for {}\n'.format(jid))
            file.write('## Set of feeds exported with Slixfeed\n')
            for result in results:
                file.write('- [{}]({})\n'.format(result[1], result[2]))
            file.write('\n\n* * *\n\nThis list was saved on {} from xmpp:{} using '
                       '[Slixfeed](https://slixfeed.woodpeckersnest.space/)\n'
                       .format(dt.current_date(), jid))


    def log_to_markdown(timestamp, filename, jid, message):
        """
        Log message to a markdown file.
    
        Parameters
        ----------
        timestamp : str
            Time stamp.
        filename : str
            Jabber ID as name of file.
        jid : str
            Jabber ID.
        message : str
            Message content.
    
        Returns
        -------
        None.
        
        """
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: timestamp: {} filename: {} jid: {} message: {}'.format(function_name, timestamp, filename, jid, message))
        with open(filename + '.md', 'a') as file:
            # entry = "{} {}:\n{}\n\n".format(timestamp, jid, message)
            entry = '## {}\n### {}\n\n{}\n\n'.format(jid, timestamp, message)
            file.write(entry)


"""

Consider utilizing a dict as a handler that would match task keyword to functions.

tasks_xmpp_chat =  {"check" : check_updates,
                    "status" : task_status_message,
                    "interval" : task_message}

tasks_xmpp_pubsub =  {"check" : check_updates,
                      "pubsub" : task_pubsub}

"""


class Task:


    def start(self, jid_bare, callback):
        callback(self, jid_bare)


    def stop(self, jid_bare, task):
        if (jid_bare in self.task_manager and
            task in self.task_manager[jid_bare]):
            self.task_manager[jid_bare][task].cancel()
        else:
            logger.debug('No task {} for JID {} (Task.stop)'
                         .format(task, jid_bare))


"""

FIXME

1) Do not handle base64
   https://www.lilithsaintcrow.com/2024/02/love-anonymous/
   data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAABaAAAAeAAQAAAAAQ6M16AAAAAnRSTlMAAHaTzTgAAAFmSURBVBgZ7cEBAQAAAIKg/q92SMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADgWE3LAAGyZmPPAAAAAElFTkSuQmCC
   https://www.lilithsaintcrow.com/2024/02/love-anonymous//image/png;base64,iVBORw0KGgoAAAANSUhEUgAABaAAAAeAAQAAAAAQ6M16AAAAAnRSTlMAAHaTzTgAAAFmSURBVBgZ7cEBAQAAAIKg/q92SMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADgWE3LAAGyZmPPAAAAAElFTkSuQmCC

TODO

1) ActivityPub URL revealer activitypub_to_http.

2) SQLite preference "instance" for preferred instances.

"""


class Url:

# NOTE
# hostname and protocol are listed as one in file proxies.toml.
# Perhaps a better practice would be to have them separated.

# NOTE
# File proxies.toml will remain as it is, in order to be
# coordinated with the dataset of project LibRedirect, even
# though rule-sets might be adopted (see )Privacy Redirect).

    def get_hostname(url):
        parted_url = urlsplit(url)
        hostname = parted_url.netloc
        if hostname.startswith('www.'): hostname = hostname.replace('www.', '')
        return hostname
    
    
    async def replace_hostname(url, url_type):
        """
        Replace hostname.
    
        Parameters
        ----------
        url : str
            URL.
        url_type : str
            "feed" or "link".
    
        Returns
        -------
        url : str
            URL.
        """
        url_new = None
        parted_url = urlsplit(url)
        # protocol = parted_url.scheme
        hostname = parted_url.netloc
        hostname = hostname.replace('www.','')
        pathname = parted_url.path
        queries = parted_url.query
        fragment = parted_url.fragment
        proxies = config.open_config_file('proxies.toml')['proxies']
        for proxy_name in proxies:
            proxy = proxies[proxy_name]
            if hostname in proxy['hostname'] and url_type in proxy['type']:
                while not url_new:
                    print('>>>')
                    print(url_new)
                    proxy_type = 'clearnet'
                    proxy_list = proxy[proxy_type]
                    if len(proxy_list):
                        # proxy_list = proxies[proxy_name][proxy_type]
                        proxy_url = random.choice(proxy_list)
                        parted_proxy_url = urlsplit(proxy_url)
                        protocol_new = parted_proxy_url.scheme
                        hostname_new = parted_proxy_url.netloc
                        url_new = urlunsplit([protocol_new, hostname_new,
                                              pathname, queries, fragment])
                        print(proxy_url)
                        print(url_new)
                        print('>>>')
                        response = await fetch.http(url_new)
                        if (response and
                            response['status_code'] == 200 and
                            # response.reason == 'OK' and
                            url_new.startswith(proxy_url)):
                            break
                        else:
                            config_dir = config.get_default_config_directory()
                            proxies_obsolete_file = config_dir + '/proxies_obsolete.toml'
                            proxies_file = config_dir + '/proxies.toml'
                            if not os.path.isfile(proxies_obsolete_file):
                                config.create_skeleton(proxies_file)
                            config.backup_obsolete(proxies_obsolete_file,
                                                   proxy_name, proxy_type,
                                                   proxy_url)
                            try:
                                config.update_proxies(proxies_file, proxy_name,
                                                      proxy_type, proxy_url)
                            except ValueError as e:
                                logger.error([str(e), proxy_url])
                            url_new = None
                    else:
                        logger.warning('No proxy URLs for {}. '
                                       'Please update proxies.toml'
                                       .format(proxy_name))
                        url_new = url
                        break
        return url_new
    
    
    def remove_tracking_parameters(url):
        """
        Remove queries with tracking parameters.
    
        Parameters
        ----------
        url : str
            URL.
    
        Returns
        -------
        url : str
            URL.
        """
        if url.startswith('data:') and ';base64,' in url:
            return url
        parted_url = urlsplit(url)
        protocol = parted_url.scheme
        hostname = parted_url.netloc
        pathname = parted_url.path
        queries = parse_qs(parted_url.query)
        fragment = parted_url.fragment
        trackers = config.open_config_file('queries.toml')['trackers']
        for tracker in trackers:
            if tracker in queries: del queries[tracker]
        queries_new = urlencode(queries, doseq=True)
        url = urlunsplit([protocol, hostname, pathname, queries_new, fragment])
        return url
    
    
    def feed_to_http(url):
        """
        Replace scheme FEED by HTTP.
    
        Parameters
        ----------
        url : str
            URL.
    
        Returns
        -------
        new_url : str
            URL.
        """
        par_url = urlsplit(url)
        new_url = urlunsplit(['http', par_url.netloc, par_url.path, par_url.query,
                              par_url.fragment])
        return new_url
    
    
    def check_xmpp_uri(uri):
        """
        Check validity of XMPP URI.
    
        Parameters
        ----------
        uri : str
            URI.
    
        Returns
        -------
        jid : str
            JID or None.
        """
        jid = urlsplit(uri).path
        if parseaddr(jid)[1] != jid:
            jid = False
        return jid
    
    
    # NOTE Read the documentation
    # https://docs.python.org/3/library/urllib.parse.html#urllib.parse.urljoin
    def complete_url(source, link):
        """
        Check if URL is pathname and complete it into URL.
    
        Parameters
        ----------
        source : str
            Feed URL.
        link : str
            Link URL or pathname.
    
        Returns
        -------
        str
            URL.
        """
        if link.startswith('data:') and ';base64,' in link:
            return link
        if link.startswith('www.'):
            return 'http://' + link
        parted_link = urlsplit(link)
        parted_feed = urlsplit(source)
        if parted_link.scheme == 'magnet' and parted_link.query:
            return link
        if parted_link.scheme and parted_link.netloc:
            return link
        if link.startswith('//'):
            if parted_link.netloc and parted_link.path:
                new_link = urlunsplit([parted_feed.scheme, parted_link.netloc,
                                       parted_link.path, parted_link.query,
                                       parted_link.fragment])
        elif link.startswith('/'):
            new_link = urlunsplit([parted_feed.scheme, parted_feed.netloc,
                                   parted_link.path, parted_link.query,
                                   parted_link.fragment])
        elif link.startswith('../'):
            pathlink = parted_link.path.split('/')
            pathfeed = parted_feed.path.split('/')
            for i in pathlink:
                if i == '..':
                    if pathlink.index('..') == 0:
                        pathfeed.pop()
                    else:
                        break
            while pathlink.count('..'):
                if pathlink.index('..') == 0:
                    pathlink.remove('..')
                else:
                    break
            pathlink = '/'.join(pathlink)
            pathfeed.extend([pathlink])
            new_link = urlunsplit([parted_feed.scheme, parted_feed.netloc,
                                   '/'.join(pathfeed), parted_link.query,
                                   parted_link.fragment])
        else:
            pathlink = parted_link.path.split('/')
            pathfeed = parted_feed.path.split('/')
            if link.startswith('./'):
                pathlink.remove('.')
            if not source.endswith('/'):
                pathfeed.pop()
            pathlink = '/'.join(pathlink)
            pathfeed.extend([pathlink])
            new_link = urlunsplit([parted_feed.scheme, parted_feed.netloc,
                                   '/'.join(pathfeed), parted_link.query,
                                   parted_link.fragment])
        return new_link
    
    
    
    # TODO
    
    # Feed https://www.ocaml.org/feed.xml
    # Link %20https://frama-c.com/fc-versions/cobalt.html%20
    
    # FIXME
    
    # Feed https://cyber.dabamos.de/blog/feed.rss
    # Link https://cyber.dabamos.de/blog/#article-2022-07-15
    
    def join_url(source, link):
        """
        Join base URL with given pathname.
    
        Parameters
        ----------
        source : str
            Feed URL.
        link : str
            Link URL or pathname.
    
        Returns
        -------
        str
            URL.
        """
        if link.startswith('data:') and ';base64,' in link:
            return link
        if link.startswith('www.'):
            new_link = 'http://' + link
        elif link.startswith('%20') and link.endswith('%20'):
            old_link = link.split('%20')
            del old_link[0]
            old_link.pop()
            new_link = ''.join(old_link)
        else:
            new_link = urljoin(source, link)
        return new_link
    
    
    def trim_url(url):
        """
        Check URL pathname for double slash.
    
        Parameters
        ----------
        url : str
            URL.
    
        Returns
        -------
        url : str
            URL.
        """
        if url.startswith('data:') and ';base64,' in url:
            return url
        parted_url = urlsplit(url)
        protocol = parted_url.scheme
        hostname = parted_url.netloc
        pathname = parted_url.path
        queries = parted_url.query
        fragment = parted_url.fragment
        while '//' in pathname:
            pathname = pathname.replace('//', '/')
        url = urlunsplit([protocol, hostname, pathname, queries, fragment])
        return url
    
    
    def activitypub_to_http(namespace):
        """
        Replace ActivityPub namespace by HTTP.
    
        Parameters
        ----------
        namespace : str
            Namespace.
    
        Returns
        -------
        new_url : str
            URL.
        """



class String:


    def generate_identifier(url, counter):
        hostname = Url.get_hostname(url)
        hostname = hostname.replace('.','-')
        identifier = hostname + ':' + str(counter)
        return identifier


    # string_to_md5_hash
    # NOTE Warning: Entry might not have a link
    # TODO Handle situation error
    def md5_hash(url):
        url_encoded = url.encode()
        url_hashed = hashlib.md5(url_encoded)
        url_digest = url_hashed.hexdigest()
        return url_digest



class Utilities:


    # string_to_md5_hash
    # NOTE Warning: Entry might not have a link
    # TODO Handle situation error
    def hash_url_to_md5(url):
        url_encoded = url.encode()
        url_hashed = hashlib.md5(url_encoded)
        url_digest = url_hashed.hexdigest()
        return url_digest


    def pick_a_feed(lang=None):
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: lang: {}'
                    .format(function_name, lang))
        config_dir = config.get_default_config_directory()
        with open(config_dir + '/' + 'feeds.toml', mode="rb") as feeds:
            urls = tomllib.load(feeds)
        import random
        url = random.choice(urls['feeds'])
        return url
