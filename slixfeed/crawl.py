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

"""

from aiohttp import ClientError, ClientSession, ClientTimeout
from feedparser import parse
from lxml import html
import slixfeed.config as config
from slixfeed.fetch import download_feed
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
        print("RSS Auto-Discovery Engaged")
        result = await feed_mode_auto_discovery(url, tree)
    if not result:
        print("RSS Scan Mode Engaged")
        result = await feed_mode_scan(url, tree)
    if not result:
        print("RSS Arbitrary Mode Engaged")
        result = await feed_mode_request(url, tree)
    if not result:
        result = (
            "> {}\nNo news feeds were found for URL."
            ).format(url)
    return result


# TODO Improve scan by gradual decreasing of path
async def feed_mode_request(url, tree):
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
    feeds = {}
    parted_url = urlsplit(url)
    paths = config.get_list("lists.yaml", "pathnames")
    for path in paths:
        address = urlunsplit([
            parted_url.scheme,
            parted_url.netloc,
            path,
            None,
            None
            ])
        res = await download_feed(address)
        if res[1] == 200:
            # print(parse(res[0])["feed"]["title"])
            # feeds[address] = parse(res[0])["feed"]["title"]
            try:
                title = parse(res[0])["feed"]["title"]
            except:
                title = '*** No Title ***'
            feeds[address] = title
        # Check whether URL has path (i.e. not root)
        # Check parted_url.path to avoid error in case root wasn't given
        # TODO Make more tests
        if parted_url.path and parted_url.path.split('/')[1]:
            paths.extend(
                [".atom", ".feed", ".rdf", ".rss"]
                ) if '.rss' not in paths else -1
            # if paths.index('.rss'):
            #     paths.extend([".atom", ".feed", ".rdf", ".rss"])
            address = urlunsplit([
                parted_url.scheme,
                parted_url.netloc,
                parted_url.path.split('/')[1] + path,
                None,
                None
                ])
            res = await download_feed(address)
            if res[1] == 200:
                try:
                    feeds[address] = parse(res[0])
                    # print(feeds)
                except:
                    continue
    # TODO return feeds
    if len(feeds) > 1:
        counter = 0
        msg = (
            "RSS URL discovery has found {} feeds:\n\n```\n"
            ).format(len(feeds))
        feed_mark = 0
        for feed in feeds:
            try:
                feed_name = feeds[feed]["feed"]["title"]
            except:
                feed_name = urlsplit(feed).netloc
            feed_addr = feed
            # AttributeError: 'str' object has no attribute 'entries'
            try:
                feed_amnt = len(feeds[feed].entries)
            except:
                continue
            if feed_amnt:
                # NOTE Because there could be many false positives
                # which are revealed in second phase of scan, we
                # could end with a single feed, which would be
                # listed instead of fetched, so feed_mark is
                # utilized in order to make fetch possible.
                feed_mark = [feed_addr]
                counter += 1
                msg += (
                    "Title: {}\n"
                    "Link : {}\n"
                    "Items: {}\n"
                    "\n"
                    ).format(feed_name, feed_addr, feed_amnt)
        if counter > 1:
            msg += (
                "```\nThe above feeds were extracted from\n{}"
                ).format(url)
        elif feed_mark:
            return feed_mark
        else:
            msg = (
                "No feeds were found for {}"
                ).format(url)
        return msg
    elif feeds:
        return feeds


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
    feeds = {}
    # paths = []
    # TODO Test
    paths = config.get_list("lists.yaml", "pathnames")
    for path in paths:
        # xpath_query = "//*[@*[contains(.,'{}')]]".format(path)
        # xpath_query = "//a[contains(@href,'{}')]".format(path)
        num = 5
        xpath_query = "(//a[contains(@href,'{}')])[position()<={}]".format(path, num)
        addresses = tree.xpath(xpath_query)
        xpath_query = "(//a[contains(@href,'{}')])[position()>last()-{}]".format(path, num)
        addresses += tree.xpath(xpath_query)
        parted_url = urlsplit(url)
        # NOTE Should number of addresses be limited or
        # perhaps be N from the start and N from the end
        for address in addresses:
            # print(address.xpath('@href')[0])
            # print(addresses)
            address = address.xpath('@href')[0]
            if "/" not in address:
                protocol = parted_url.scheme
                hostname = parted_url.netloc
                pathname = address
                address = urlunsplit([
                    protocol,
                    hostname,
                    pathname,
                    None,
                    None
                    ])
            if address.startswith('/'):
                protocol = parted_url.scheme
                hostname = parted_url.netloc
                pathname = address
                address = urlunsplit([
                    protocol,
                    hostname,
                    pathname,
                    None,
                    None
                    ])
            res = await download_feed(address)
            if res[1] == 200:
                try:
                    feeds[address] = parse(res[0])
                    # print(feeds[address])
                    # breakpoint()
                    # print(feeds)
                except:
                    continue
    # TODO return feeds
    if len(feeds) > 1:
        # print(feeds)
        # breakpoint()
        counter = 0
        msg = (
            "RSS URL scan has found {} feeds:\n\n```\n"
            ).format(len(feeds))
        feed_mark = 0
        for feed in feeds:
            # try:
            #     res = await download_feed(feed)
            # except:
            #     continue
            try:
                feed_name = feeds[feed]["feed"]["title"]
            except:
                feed_name = urlsplit(feed).netloc
            feed_addr = feed
            feed_amnt = len(feeds[feed].entries)
            if feed_amnt:
                # NOTE Because there could be many false positives
                # which are revealed in second phase of scan, we
                # could end with a single feed, which would be
                # listed instead of fetched, so feed_mark is
                # utilized in order to make fetch possible.
                feed_mark = [feed_addr]
                counter += 1
                msg += (
                    "Title : {}\n"
                    "Link  : {}\n"
                    "Count : {}\n"
                    "\n"
                    ).format(feed_name, feed_addr, feed_amnt)
        if counter > 1:
            msg += (
                "```\nThe above feeds were extracted from\n{}"
                ).format(url)
        elif feed_mark:
            return feed_mark
        else:
            msg = (
                "No feeds were found for {}"
                ).format(url)
        return msg
    elif feeds:
        return feeds


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
    # TODO return feeds
    if len(feeds) > 1:
        msg = (
            "RSS Auto-Discovery has found {} feeds:\n\n```\n"
            ).format(len(feeds))
        for feed in feeds:
            # # The following code works;
            # # The following code will catch
            # # only valid resources (i.e. not 404);
            # # The following code requires more bandwidth.
            # res = await download_feed(feed)
            # if res[0]:
            #     disco = parse(res[0])
            #     title = disco["feed"]["title"]
            #     msg += "{} \n {} \n\n".format(title, feed)
            feed_name = feed.xpath('@title')[0]
            feed_addr = join_url(url, feed.xpath('@href')[0])
            # if feed_addr.startswith("/"):
            #     feed_addr = url + feed_addr
            msg += "{}\n{}\n\n".format(feed_name, feed_addr)
        msg += (
            "```\nThe above feeds were extracted from\n{}"
            ).format(url)
        return msg
    elif feeds:
        feed_addr = join_url(url, feeds[0].xpath('@href')[0])
        return [feed_addr]
