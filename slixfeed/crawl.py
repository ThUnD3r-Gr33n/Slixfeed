#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

TODO

1.1) Do not compose messages.
     Only return results.
     See: # TODO return feeds

1.2) Return URLs, nothing else other (e.g. processed messages).

1.3) NOTE: Correction of URLs is aceptable.

2) Consider merging with module fetch.py

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
from lxml import html
import slixfeed.config as config
import slixfeed.fetch as fetch
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


async def probe_page(url, document):
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
    result = None
    try:
        # tree = etree.fromstring(res[0]) # etree is for xml
        tree = html.fromstring(document)
    except:
        result = (
            "> {}\nFailed to parse URL as feed."
            ).format(url)
    if not result:
        logging.debug(
            "Feed auto-discovery engaged for {}".format(url))
        result = await feed_mode_auto_discovery(url, tree)
    if not result:
        logging.debug(
            "Feed link scan mode engaged for {}".format(url))
        result = await feed_mode_scan(url, tree)
    if not result:
        logging.debug(
            "Feed arbitrary mode engaged for {}".format(url))
        result = await feed_mode_guess(url, tree)
    if not result:
        logging.debug(
            "No feeds were found for {}".format(url))
        result = (
            "> {}\nNo news feeds were found for URL."
            ).format(url)
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
    paths = config.get_list("lists.toml", "pathnames")
    # Check whether URL has path (i.e. not root)
    # Check parted_url.path to avoid error in case root wasn't given
    # TODO Make more tests
    if parted_url.path and parted_url.path.split('/')[1]:
        paths.extend(
            [".atom", ".feed", ".rdf", ".rss"]
            ) if '.rss' not in paths else -1
        # if paths.index('.rss'):
        #     paths.extend([".atom", ".feed", ".rdf", ".rss"])
    for path in paths:
        address = join_url(url, parted_url.path.split('/')[1] + path)
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
    paths = config.get_list("lists.toml", "pathnames")
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
        res = await fetch.http(i)
        if res[1] == 200:
            try:
                feeds[i] = [parse(res[0])]
            except:
                continue
    message = (
        "Web feeds found for {}\n\n```\n"
        ).format(url)
    counter = 0
    feed_url_mark = 0
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
            # which are revealed in second phase of scan, we
            # could end with a single feed, which would be
            # listed instead of fetched, so feed_url_mark is
            # utilized in order to make fetch possible.
            feed_url_mark = [feed_url]
            counter += 1
            message += (
                "Title : {}\n"
                "Link  : {}\n"
                "\n"
                ).format(feed_name, feed_url)
    if counter > 1:
        message += (
            "```\nTotal of {} feeds."
            ).format(counter)
        result = message
    elif feed_url_mark:
        result = feed_url_mark
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