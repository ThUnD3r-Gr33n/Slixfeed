#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

FIXME

1) https://wiki.pine64.org
     File "/slixfeed/crawl.py", line 178, in feed_mode_guess
       address = join_url(url, parted_url.path.split('/')[1] + path)
                               ~~~~~~~~~~~~~~~~~~~~~~~~~~^^^
   IndexError: list index out of range

TODO

1.1) Attempt to scan more paths: /blog/, /news/ etc., including root / 
   Attempt to scan sub domains
   https://esmailelbob.xyz/en/
   https://blog.esmailelbob.xyz/feed/

1.2) Consider utilizing fetch.http_response

2) Consider merging with module fetch.py

FEEDS CRAWLER PROJECT

3) Mark redirects for manual check

Title : JSON Feed
Link  : https://www.jsonfeed.org/feed.json.xml

Title : JSON Feed
Link  : https://www.jsonfeed.org/feed.json/atom.xml

Title : JSON Feed
Link  : https://www.jsonfeed.org/feed.json/feed.xml

Title : JSON Feed
Link  : https://www.jsonfeed.org/feed.json/feeds/rss/news.xml.php

Title : JSON Feed
Link  : https://www.jsonfeed.org/feed.json/jekyll/feed.xml

Title : JSON Feed
Link  : https://www.jsonfeed.org/feed.json/news.xml

Title : JSON Feed
Link  : https://www.jsonfeed.org/feed.json/news.xml.php

Title : JSON Feed
Link  : https://www.jsonfeed.org/feed.json/rdf.xml

Title : JSON Feed
Link  : https://www.jsonfeed.org/feed.json/rss.xml

Title : JSON Feed
Link  : https://www.jsonfeed.org/feed.json/videos.xml


"""

from aiohttp import ClientError, ClientSession, ClientTimeout
from feedparser import parse
import logging
from lxml import etree
from lxml import html
from lxml.etree import fromstring
import slixfeed.config as config
import slixfeed.fetch as fetch
from slixfeed.log import Logger
from slixfeed.url import complete_url, join_url, trim_url
from urllib.parse import urlsplit, urlunsplit


# TODO Use boolean as a flag to determine whether a single URL was found
# async def probe_page(
#     callback, url, document, num=None, db_file=None):
#     result = None
#     try:
#         # tree = etree.fromstring(res[0]) # etree is for xml
#         tree = html.fromstring(document)
#     except:
#         result = (
#             "> {}\nFailed to parse URL as feed."
#             ).format(url)
#     if not result:
#         print("RSS Auto-Discovery Engaged")
#         result = await feed_mode_auto_discovery(url, tree)
#     if not result:
#         print("RSS Scan Mode Engaged")
#         result = await feed_mode_scan(url, tree)
#     if not result:
#         print("RSS Arbitrary Mode Engaged")
#         result = await feed_mode_request(url, tree)
#     if not result:
#         result = (
#             "> {}\nNo news feeds were found for URL."
#             ).format(url)
#     # elif msg:
#     else:
#         if isinstance(result, str):
#             return result
#         elif isinstance(result, list):
#             url = result[0]
#             if db_file:
#                 # print("if db_file", db_file)
#                 return await callback(db_file, url)
#             elif num:
#                 return await callback(url, num)
#             else:
#                 return await callback(url)

logger = Logger(__name__)

async def probe_page(url, document=None):
    """
    Parameters
    ----------
    url : str
        URL.
    document : TYPE
        DESCRIPTION.

    Returns
    -------
    result : list or str
        Single URL as list or selection of URLs as str.
    """
    if not document:
        response = await fetch.http(url)
        if not response['error']:
            document = response['content']
    try:
        # tree = etree.fromstring(res[0]) # etree is for xml
        tree = html.fromstring(document)
        result = None
    except Exception as e:
        logger.error(str(e))
        try:
            # /questions/15830421/xml-unicode-strings-with-encoding-declaration-are-not-supported
            # xml = html.fromstring(document.encode('utf-8'))
            # parser = etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')
            # tree = fromstring(xml, parser=parser)

            # /questions/57833080/how-to-fix-unicode-strings-with-encoding-declaration-are-not-supported
            #tree = html.fromstring(bytes(document, encoding='utf8'))

            # https://twigstechtips.blogspot.com/2013/06/python-lxml-strings-with-encoding.html
            #parser = etree.XMLParser(recover=True)
            #tree = etree.fromstring(document, parser)

            tree = html.fromstring(document.encode('utf-8'))
            result = None
        except Exception as e:
            logger.error(str(e))
            logger.warning("Failed to parse URL as feed for {}.".format(url))
            result = {'link' : None,
                      'index' : None,
                      'name' : None,
                      'code' : None,
                      'error' : True,
                      'exist' : None}
    if not result:
        logger.debug("Feed auto-discovery engaged for {}".format(url))
        result = await feed_mode_auto_discovery(url, tree)
    if not result:
        logger.debug("Feed link scan mode engaged for {}".format(url))
        result = await feed_mode_scan(url, tree)
    if not result:
        logger.debug("Feed arbitrary mode engaged for {}".format(url))
        result = await feed_mode_guess(url, tree)
    if not result:
        logger.debug("No feeds were found for {}".format(url))
        result = None
    return result


# TODO Improve scan by gradual decreasing of path
async def feed_mode_guess(url, tree):
    """
    Lookup for feeds by pathname using HTTP Requests.

    Parameters
    ----------
    db_file : str
        Path to database file.
    url : str
        URL.
    tree : TYPE
        DESCRIPTION.

    Returns
    -------
    msg : str
        Message with URLs.
    """
    urls = []
    parted_url = urlsplit(url)
    paths = config.open_config_file("lists.toml")["pathnames"]
    # Check whether URL has path (i.e. not root)
    # Check parted_url.path to avoid error in case root wasn't given
    # TODO Make more tests
    if parted_url.path and parted_url.path.split('/')[1]:
        paths.extend(
            [".atom", ".feed", ".rdf", ".rss"]
            ) if '.rss' not in paths else -1
        # if paths.index('.rss'):
        #     paths.extend([".atom", ".feed", ".rdf", ".rss"])
    parted_url_path = parted_url.path if parted_url.path else '/'
    for path in paths:
        address = join_url(url, parted_url_path.split('/')[1] + path)
        if address not in urls:
            urls.extend([address])
    # breakpoint()
    # print("feed_mode_guess")
    urls = await process_feed_selection(url, urls)
    return urls


async def feed_mode_scan(url, tree):
    """
    Scan page for potential feeds by pathname.

    Parameters
    ----------
    db_file : str
        Path to database file.
    url : str
        URL.
    tree : TYPE
        DESCRIPTION.

    Returns
    -------
    msg : str
        Message with URLs.
    """
    urls = []
    paths = config.open_config_file("lists.toml")["pathnames"]
    for path in paths:
        # xpath_query = "//*[@*[contains(.,'{}')]]".format(path)
        # xpath_query = "//a[contains(@href,'{}')]".format(path)
        num = 5
        xpath_query = (
            "(//a[contains(@href,'{}')])[position()<={}]"
            ).format(path, num)
        addresses = tree.xpath(xpath_query)
        xpath_query = (
            "(//a[contains(@href,'{}')])[position()>last()-{}]"
            ).format(path, num)
        addresses += tree.xpath(xpath_query)
        # NOTE Should number of addresses be limited or
        # perhaps be N from the start and N from the end
        for address in addresses:
            address = join_url(url, address.xpath('@href')[0])
            if address not in urls:
                urls.extend([address])
    # breakpoint()
    # print("feed_mode_scan")
    urls = await process_feed_selection(url, urls)
    return urls


async def feed_mode_auto_discovery(url, tree):
    """
    Lookup for feeds using RSS autodiscovery technique.

    See: https://www.rssboard.org/rss-autodiscovery

    Parameters
    ----------
    db_file : str
        Path to database file.
    url : str
        URL.
    tree : TYPE
        DESCRIPTION.

    Returns
    -------
    msg : str
        Message with URLs.
    """
    xpath_query = (
        '//link[(@rel="alternate") and '
        '(@type="application/atom+xml" or '
        '@type="application/rdf+xml" or '
        '@type="application/rss+xml")]'
        )
    # xpath_query = """//link[(@rel="alternate") and (@type="application/atom+xml" or @type="application/rdf+xml" or @type="application/rss+xml")]/@href"""
    # xpath_query = "//link[@rel='alternate' and @type='application/atom+xml' or @rel='alternate' and @type='application/rss+xml' or @rel='alternate' and @type='application/rdf+xml']/@href"
    feeds = tree.xpath(xpath_query)
    if feeds:
        urls = []
        for feed in feeds:
            # # The following code works;
            # # The following code will catch
            # # only valid resources (i.e. not 404);
            # # The following code requires more bandwidth.
            # res = await fetch.http(feed)
            # if res[0]:
            #     disco = parse(res[0])
            #     title = disco["feed"]["title"]
            #     msg += "{} \n {} \n\n".format(title, feed)

            # feed_name = feed.xpath('@title')[0]
            # feed_addr = join_url(url, feed.xpath('@href')[0])

            # if feed_addr.startswith("/"):
            #     feed_addr = url + feed_addr
            address = join_url(url, feed.xpath('@href')[0])
            if address not in urls:
                urls.extend([address])
        # breakpoint()
        # print("feed_mode_auto_discovery")
        urls = await process_feed_selection(url, urls)
        return urls


# TODO Segregate function into function that returns
# URLs (string) and Feeds (dict) and function that
# composes text message (string).
# Maybe that's not necessary.
async def process_feed_selection(url, urls):
    feeds = {}
    for i in urls:
        result = await fetch.http(i)
        if not result['error']:
            document = result['content']
            status_code = result['status_code']
            if status_code == 200: # NOTE This line might be redundant
                try:
                    feeds[i] = [parse(document)]
                except:
                    continue
    message = (
        "Web feeds found for {}\n\n```\n"
        ).format(url)
    urls = []
    for feed_url in feeds:
        # try:
        #     res = await fetch.http(feed)
        # except:
        #     continue
        feed_name = None
        if "title" in feeds[feed_url][0]["feed"].keys():
            feed_name = feeds[feed_url][0].feed.title
        feed_name = feed_name if feed_name else "Untitled"
        # feed_name = feed_name if feed_name else urlsplit(feed_url).netloc
        # AttributeError: 'str' object has no attribute 'entries'
        if "entries" in feeds[feed_url][0].keys():
            feed_amnt = feeds[feed_url][0].entries
        else:
            continue
        if feed_amnt:
            # NOTE Because there could be many false positives
            #      which are revealed in second phase of scan, we
            #      could end with a single feed, which would be
            #      listed instead of fetched, so feed_url_mark is
            #      utilized in order to make fetch possible.
            # NOTE feed_url_mark was a variable which stored
            #      single URL (probably first accepted as valid)
            #      in order to get an indication whether a single
            #      URL has been fetched, so that the receiving
            #      function will scan that single URL instead of
            #      listing it as a message.
            url = {'link' : feed_url,
                   'index' : None,
                   'name' : feed_name,
                   'code' : status_code,
                   'error' : False,
                   'exist' : None}
            urls.extend([url])
    count = len(urls)
    if count > 1:
        result = urls
    elif count:
        result = urls[0]
    else:
        result = None
    return result


# def get_discovered_feeds(url, urls):
#     message = (
#         "Found {} web feeds:\n\n```\n"
#         ).format(len(urls))
#     if len(urls) > 1:
#         for urls in urls:
#                 message += (
#                     "Title : {}\n"
#                     "Link  : {}\n"
#                     "\n"
#                     ).format(url, url.title)
#         message += (
#             "```\nThe above feeds were extracted from\n{}"
#             ).format(url)
#     elif len(urls) > 0:
#         result = urls
#     else:
#         message = (
#             "No feeds were found for {}"
#             ).format(url)
#     return result


# Test module
# TODO ModuleNotFoundError: No module named 'slixfeed'
# import slixfeed.fetch as fetch
# from slixfeed.action import is_feed, process_feed_selection

# async def start(url):
#     while True:
#         result = await fetch.http(url)
#         document = result[0]
#         status = result[1]
#         if document:
#             feed = parse(document)
#             if is_feed(feed):
#                 print(url)
#             else:
#                 urls = await probe_page(
#                     url, document)
#                 if len(urls) > 1:
#                     await process_feed_selection(urls)
#                 elif urls:
#                     url = urls[0]
#         else:
#             response = (
#                 "> {}\nFailed to load URL.  Reason: {}"
#                 ).format(url, status)
#             break
#     return response

# url = "https://www.smh.com.au/rssheadlines"
# start(url)
