#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

FIXME

1) feed_mode_scan doesn't find feed for https://www.blender.org/
   even though it should be according to the pathnames dictionary.

TODO

1) Support Gemini and Gopher.

"""

import aiohttp
import asyncio
import feedparser

import sqlitehandler
import confighandler
import datetimehandler
import listhandler

from asyncio.exceptions import IncompleteReadError
from http.client import IncompleteRead
from urllib import error
from bs4 import BeautifulSoup
# from xml.etree.ElementTree import ElementTree, ParseError
from urllib.parse import urljoin
from urllib.parse import urlsplit
from urllib.parse import urlunsplit
from lxml import html


# NOTE Why (if res[0]) and (if res[1] == 200)?
async def download_updates(db_file, url=None):
    """
    Check feeds for new entries.

    Parameters
    ----------
    db_file : str
        Path to database file.
    url : str, optional
        URL. The default is None.
    """
    if url:
        urls = [url] # Valid [url] and [url,] and (url,)
    else:
        urls = await sqlitehandler.get_feeds_url(db_file)
    for url in urls:
        # print(os.path.basename(db_file), url[0])
        source = url[0]
        res = await download_feed(source)
        # TypeError: 'NoneType' object is not subscriptable
        if res is None:
            # Skip to next feed
            # urls.next()
            # next(urls)
            continue
        await sqlitehandler.update_source_status(
            db_file,
            res[1],
            source
            )
        if res[0]:
            try:
                feed = feedparser.parse(res[0])
                if feed.bozo:
                    # bozo = (
                    #     "WARNING: Bozo detected for feed: {}\n"
                    #     "For more information, visit "
                    #     "https://pythonhosted.org/feedparser/bozo.html"
                    #     ).format(source)
                    # print(bozo)
                    valid = 0
                else:
                    valid = 1
                await sqlitehandler.update_source_validity(
                    db_file,
                    source,
                    valid)
            except (
                    IncompleteReadError,
                    IncompleteRead,
                    error.URLError
                    ) as e:
                # print(e)
                # TODO Print error to log
                None
                # NOTE I don't think there should be "return"
                # because then we might stop scanning next URLs
                # return
        # TODO Place these couple of lines back down
        # NOTE Need to correct the SQL statement to do so
        # NOT SURE WHETHER I MEANT THE LINES ABOVE OR BELOW
        if res[1] == 200:
        # NOT SURE WHETHER I MEANT THE LINES ABOVE OR BELOW
        # TODO Place these couple of lines back down
        # NOTE Need to correct the SQL statement to do so
            entries = feed.entries
            # length = len(entries)
            # await sqlitehandler.remove_entry(db_file, source, length)
            await sqlitehandler.remove_nonexistent_entries(
                db_file,
                feed,
                source
                )
            # new_entry = 0
            for entry in entries:
                # TODO Pass date too for comparion check
                if entry.has_key("published"):
                    date = entry.published
                    date = await datetimehandler.rfc2822_to_iso8601(date)
                elif entry.has_key("updated"):
                    date = entry.updated
                    date = await datetimehandler.rfc2822_to_iso8601(date)
                else:
                    # TODO Just set date = "*** No date ***"
                    # date = await datetime.now().isoformat()
                    date = await datetimehandler.now()
                    # NOTE Would seconds result in better database performance
                    # date = datetime.datetime(date)
                    # date = (date-datetime.datetime(1970,1,1)).total_seconds()
                if entry.has_key("title"):
                    title = entry.title
                    # title = "{}: *{}*".format(feed["feed"]["title"], entry.title)
                else:
                    title = date
                    # title = feed["feed"]["title"]
                if entry.has_key("link"):
                    # link = complete_url(source, entry.link)
                    link = await join_url(source, entry.link)
                    link = await trim_url(link)
                else:
                    link = source
                if entry.has_key("id"):
                    eid = entry.id
                else:
                    eid = link
                exist = await sqlitehandler.check_entry_exist(
                    db_file,
                    source,
                    eid=eid,
                    title=title,
                    link=link,
                    date=date
                    )
                if not exist:
                    # new_entry = new_entry + 1
                    # TODO Enhance summary
                    if entry.has_key("summary"):
                        summary = entry.summary
                        # # Remove HTML tags
                        # summary = BeautifulSoup(summary, "lxml").text
                        # # TODO Limit text length
                        # summary = summary.replace("\n\n\n", "\n\n")
                        # summary = summary[:300] + " […]‍⃨"
                        # summary = summary.strip().split('\n')
                        # summary = ["> " + line for line in summary]
                        # summary = "\n".join(summary)
                    else:
                        summary = "> *** No summary ***"
                    read_status = 0
                    pathname = urlsplit(link).path
                    string = (
                        "{} {} {}"
                        ).format(
                            title,
                            summary,
                            pathname
                            )
                    allow_list = await listhandler.is_listed(
                        db_file,
                        "filter-allow",
                        string
                        )
                    if not allow_list:
                        reject_list = await listhandler.is_listed(
                            db_file,
                            "filter-deny",
                            string
                            )
                        if reject_list:
                            # print(">>> REJECTED", title)
                            summary = (
                                "REJECTED {}".format(
                                    reject_list.upper()
                                    )
                                )
                            # summary = ""
                            read_status = 1
                    entry = (
                        title,
                        summary,
                        link,
                        eid,
                        source,
                        date,
                        read_status
                        )
                    if isinstance(date, int):
                        print("date is int")
                        print(date)
                        breakpoint()
                    print(source)
                    print(date)
                    await sqlitehandler.add_entry_and_set_date(
                        db_file,
                        source,
                        entry
                        )
                #     print(await datetimehandler.current_time(), entry, title)
                # else:
                #     print(await datetimehandler.current_time(), exist, title)


# NOTE Why (if result[0]) and (if result[1] == 200)?
async def view_feed(url):
    """
    Check feeds for new entries.

    Parameters
    ----------
    db_file : str
        Path to database file.
    url : str, optional
        URL. The default is None.

    Returns
    -------
    msg : str
       Feed content or error message.
    """
    result = await download_feed(url)
    if result[0]:
        try:
            feed = feedparser.parse(result[0])
            if feed.bozo:
                # msg = (
                #     ">{}\n"
                #     "WARNING: Bozo detected!\n"
                #     "For more information, visit "
                #     "https://pythonhosted.org/feedparser/bozo.html"
                #     ).format(url)
                msg = await probe_page(view_feed, url, result[0])
                return msg
        except (
                IncompleteReadError,
                IncompleteRead,
                error.URLError
                ) as e:
            # print(e)
            # TODO Print error to log
            msg = (
                "> {}\n"
                "Error: {}"
                ).format(url, e)
            breakpoint()
    if result[1] == 200:
        title = await get_title(url, result[0])
        entries = feed.entries
        msg = "Preview of {}:\n```\n".format(title)
        count = 0
        for entry in entries:
            count += 1
            if entry.has_key("title"):
                title = entry.title
            else:
                title = "*** No title ***"
            if entry.has_key("link"):
                # link = complete_url(source, entry.link)
                link = await join_url(url, entry.link)
                link = await trim_url(link)
            else:
                link = "*** No link ***"
            if entry.has_key("published"):
                date = entry.published
                date = await datetimehandler.rfc2822_to_iso8601(date)
            elif entry.has_key("updated"):
                date = entry.updated
                date = await datetimehandler.rfc2822_to_iso8601(date)
            else:
                date = "*** No date ***"
            msg += (
                "Title : {}\n"
                "Date  : {}\n"
                "Link  : {}\n"
                "Count : {}\n"
                "\n"
                ).format(
                    title,
                    date,
                    link,
                    count
                    )
            if count > 4:
                break
        msg += (
            "```\nSource: {}"
            ).format(url)
    else:
        msg = (
            ">{}\nFailed to load URL.  Reason: {}"
            ).format(url, result[1])
    return msg


# NOTE Why (if result[0]) and (if result[1] == 200)?
async def view_entry(url, num):
    result = await download_feed(url)
    if result[0]:
        try:
            feed = feedparser.parse(result[0])
            if feed.bozo:
                # msg = (
                #     ">{}\n"
                #     "WARNING: Bozo detected!\n"
                #     "For more information, visit "
                #     "https://pythonhosted.org/feedparser/bozo.html"
                #     ).format(url)
                msg = await probe_page(view_entry, url, result[0], num)
                return msg
        except (
                IncompleteReadError,
                IncompleteRead,
                error.URLError
                ) as e:
            # print(e)
            # TODO Print error to log
            msg = (
                "> {}\n"
                "Error: {}"
                ).format(url, e)
            breakpoint()
    if result[1] == 200:
        feed = feedparser.parse(result[0])
        title = await get_title(url, result[0])
        entries = feed.entries
        num = int(num) - 1
        entry = entries[num]
        if entry.has_key("title"):
            title = entry.title
        else:
            title = "*** No title ***"
        if entry.has_key("published"):
            date = entry.published
            date = await datetimehandler.rfc2822_to_iso8601(date)
        elif entry.has_key("updated"):
            date = entry.updated
            date = await datetimehandler.rfc2822_to_iso8601(date)
        else:
            date = "*** No date ***"
        if entry.has_key("summary"):
            summary = entry.summary
            # Remove HTML tags
            summary = BeautifulSoup(summary, "lxml").text
            # TODO Limit text length
            summary = summary.replace("\n\n\n", "\n\n")
        else:
            summary = "*** No summary ***"
        if entry.has_key("link"):
            # link = complete_url(source, entry.link)
            link = await join_url(url, entry.link)
            link = await trim_url(link)
        else:
            link = "*** No link ***"
        msg = (
            "{}\n"
            "\n"
            "> {}\n"
            "\n"
            "{}\n"
            "\n"
            ).format(
                title,
                summary,
                link
                )
    else:
        msg = (
            ">{}\n"
            "Failed to load URL.  Reason: {}\n"
            "Try again momentarily."
            ).format(url, result[1])
    return msg


async def add_feed_no_check(db_file, data):
    """
    Add given feed without validity check.

    Parameters
    ----------
    db_file : str
        Path to database file.
    data : str
        URL or URL and Title.

    Returns
    -------
    msg : str
       Status message.
    """
    url = data[0]
    title = data[1]
    url = await trim_url(url)
    exist = await sqlitehandler.check_feed_exist(db_file, url)
    if not exist:
        msg = await sqlitehandler.add_feed(db_file, url, title)
        await download_updates(db_file, [url])
    else:
        ix = exist[0]
        name = exist[1]
        msg = (
            "> {}\nNews source \"{}\" is already "
            "listed in the subscription list at "
            "index {}".format(url, name, ix)
            )
    return msg


async def add_feed(db_file, url):
    """
    Check whether feed exist, otherwise process it.

    Parameters
    ----------
    db_file : str
        Path to database file.
    url : str
        URL.

    Returns
    -------
    msg : str
        Status message.
    """
    msg = None
    url = await trim_url(url)
    exist = await sqlitehandler.check_feed_exist(db_file, url)
    if not exist:
        res = await download_feed(url)
        if res[0]:
            feed = feedparser.parse(res[0])
            title = await get_title(url, feed)
            if feed.bozo:
                bozo = (
                    "Bozo detected. Failed to load: {}."
                    ).format(url)
                print(bozo)
                msg = await probe_page(add_feed, url, res[0], db_file)
            else:
                status = res[1]
                msg = await sqlitehandler.add_feed(
                    db_file,
                    url,
                    title,
                    status
                    )
                await download_updates(db_file, [url])
        else:
            status = res[1]
            msg = (
                "> {}\nFailed to load URL.  Reason: {}"
                ).format(url, status)
    else:
        ix = exist[0]
        name = exist[1]
        msg = (
            "> {}\nNews source \"{}\" is already "
            "listed in the subscription list at "
            "index {}".format(url, name, ix)
            )
    return msg


# TODO callback for use with add_feed and view_feed
async def probe_page(callback, url, doc, num=None, db_file=None):
    msg = None
    try:
        # tree = etree.fromstring(res[0]) # etree is for xml
        tree = html.fromstring(doc)
    except:
        msg = (
            "> {}\nFailed to parse URL as feed."
            ).format(url)
    if not msg:
        print("RSS Auto-Discovery Engaged")
        msg = await feed_mode_auto_discovery(url, tree)
    if not msg:
        print("RSS Scan Mode Engaged")
        msg = await feed_mode_scan(url, tree)
    if not msg:
        print("RSS Arbitrary Mode Engaged")
        msg = await feed_mode_request(url, tree)
    if not msg:
        msg = (
            "> {}\nNo news feeds were found for URL."
            ).format(url)
    # elif msg:
    else:
        if isinstance(msg, str):
            return msg
        elif isinstance(msg, list):
            url = msg[0]
            if db_file:
                return await callback(db_file, url)
            elif num:
                return await callback(url, num)
            else:
                return await callback(url)


async def download_feed(url):
    """
    Download content of given URL.

    Parameters
    ----------
    url : str
        URL.

    Returns
    -------
    msg: list or str
        Document or error message.
    """
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession() as session:
    # async with aiohttp.ClientSession(trust_env=True) as session:
        try:
            async with session.get(url, timeout=timeout) as response:
                status = response.status
                if response.status == 200:
                    try:
                        doc = await response.text()
                        # print (response.content_type)
                        msg = [
                            doc,
                            status
                            ]
                    except:
                        # msg = [
                        #     False,
                        #     ("The content of this document "
                        #      "doesn't appear to be textual."
                        #      )
                        #     ]
                        msg = [
                            False,
                            "Document is too large or is not textual."
                            ]
                else:
                    msg = [
                        False,
                        "HTTP Error: " + str(status)
                        ]
        except aiohttp.ClientError as e:
            # print('Error', str(e))
            msg = [
                False,
                "Error: " + str(e)
                ]
        except asyncio.TimeoutError as e:
            # print('Timeout:', str(e))
            msg = [
                False,
                "Timeout: " + str(e)
                ]
    return msg


async def get_title(url, feed):
    """
    Get title of feed.

    Parameters
    ----------
    url : str
        URL.
    feed : dict
        Parsed feed document.

    Returns
    -------
    title : str
        Title or URL hostname.
    """
    try:
        title = feed["feed"]["title"]
    except:
        title = urlsplit(url).netloc
    return title


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
    if link.startswith("www."):
        return "http://" + link
    parted_link = urlsplit(link)
    parted_feed = urlsplit(source)
    if parted_link.scheme == "magnet" and parted_link.query:
        return link
    if parted_link.scheme and parted_link.netloc:
        return link
    if link.startswith("//"):
        if parted_link.netloc and parted_link.path:
            new_link = urlunsplit([
                parted_feed.scheme,
                parted_link.netloc,
                parted_link.path,
                parted_link.query,
                parted_link.fragment
                ])
    elif link.startswith("/"):
        new_link = urlunsplit([
            parted_feed.scheme,
            parted_feed.netloc,
            parted_link.path,
            parted_link.query,
            parted_link.fragment
            ])
    elif link.startswith("../"):
        pathlink = parted_link.path.split("/")
        pathfeed = parted_feed.path.split("/")
        for i in pathlink:
            if i == "..":
                if pathlink.index("..") == 0:
                    pathfeed.pop()
                else:
                    break
        while pathlink.count(".."):
            if pathlink.index("..") == 0:
                pathlink.remove("..")
            else:
                break
        pathlink = "/".join(pathlink)
        pathfeed.extend([pathlink])
        new_link = urlunsplit([
            parted_feed.scheme,
            parted_feed.netloc,
            "/".join(pathfeed),
            parted_link.query,
            parted_link.fragment
            ])
    else:
        pathlink = parted_link.path.split("/")
        pathfeed = parted_feed.path.split("/")
        if link.startswith("./"):
            pathlink.remove(".")
        if not source.endswith("/"):
            pathfeed.pop()
        pathlink = "/".join(pathlink)
        pathfeed.extend([pathlink])
        new_link = urlunsplit([
            parted_feed.scheme,
            parted_feed.netloc,
            "/".join(pathfeed),
            parted_link.query,
            parted_link.fragment
            ])
    return new_link


"""
TODO
Feed https://www.ocaml.org/feed.xml
Link %20https://frama-c.com/fc-versions/cobalt.html%20

FIXME
Feed https://cyber.dabamos.de/blog/feed.rss
Link https://cyber.dabamos.de/blog/#article-2022-07-15
"""
async def join_url(source, link):
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
    if link.startswith("www."):
        new_link = "http://" + link
    elif link.startswith("%20") and link.endswith("%20"):
        old_link = link.split("%20")
        del old_link[0]
        old_link.pop()
        new_link = "".join(old_link)
    else:
        new_link = urljoin(source, link)
    return new_link


async def trim_url(url):
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
    parted_url = urlsplit(url)
    protocol = parted_url.scheme
    hostname = parted_url.netloc
    pathname = parted_url.path
    queries = parted_url.query
    fragment = parted_url.fragment
    while "//" in pathname:
        pathname = pathname.replace("//", "/")
    url = urlunsplit([
        protocol,
        hostname,
        pathname,
        queries,
        fragment
        ])
    return url


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
    paths = confighandler.get_list()
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
            # print(feedparser.parse(res[0])["feed"]["title"])
            # feeds[address] = feedparser.parse(res[0])["feed"]["title"]
            try:
                title = feedparser.parse(res[0])["feed"]["title"]
            except:
                title = '*** No Title ***'
            feeds[address] = title
        # Check whether URL has path (i.e. not root)
        if parted_url.path.split('/')[1]:
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
                    feeds[address] = feedparser.parse(res[0])
                    # print(feeds)
                except:
                    continue
    if len(feeds) > 1:
        positive = 0
        msg = (
            "RSS URL discovery has found {} feeds:\n```\n"
            ).format(len(feeds))
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
                positive = 1
                msg += (
                    "Title: {}\n"
                    "Link : {}\n"
                    "Items: {}\n"
                    "\n"
                    ).format(
                        feed_name,
                        feed_addr,
                        feed_amnt
                        )
        msg += (
            "```\nThe above feeds were extracted from\n{}"
            ).format(url)
        if not positive:
            msg = (
                "No feeds were found for {}."
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
    paths = confighandler.get_list()
    for path in paths:
        # xpath_query = "//*[@*[contains(.,'{}')]]".format(path)
        xpath_query = "//a[contains(@href,'{}')]".format(path)
        addresses = tree.xpath(xpath_query)
        parted_url = urlsplit(url)
        # NOTE Should number of addresses be limited or
        # perhaps be N from the start and N from the end
        for address in addresses:
            print(address.xpath('@href')[0])
            print(addresses)
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
                    feeds[address] = feedparser.parse(res[0])
                    # print(feeds)
                except:
                    continue
    if len(feeds) > 1:
        positive = 0
        msg = (
            "RSS URL scan has found {} feeds:\n```\n"
            ).format(len(feeds))
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
                positive = 1
                msg += (
                    "Title: {}\n"
                    " Link: {}\n"
                    "Count: {}\n"
                    "\n"
                    ).format(
                        feed_name,
                        feed_addr,
                        feed_amnt
                        )
        msg += (
            "```\nThe above feeds were extracted from\n{}"
            ).format(url)
        if not positive:
            msg = (
                "No feeds were found for {}."
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
    if len(feeds) > 1:
        msg = (
            "RSS Auto-Discovery has found {} feeds:\n```\n"
            ).format(len(feeds))
        for feed in feeds:
            # # The following code works;
            # # The following code will catch
            # # only valid resources (i.e. not 404);
            # # The following code requires more bandwidth.
            # res = await download_feed(feed)
            # if res[0]:
            #     disco = feedparser.parse(res[0])
            #     title = disco["feed"]["title"]
            #     msg += "{} \n {} \n\n".format(title, feed)
            feed_name = feed.xpath('@title')[0]
            feed_addr = await join_url(url, feed.xpath('@href')[0])
            # if feed_addr.startswith("/"):
            #     feed_addr = url + feed_addr
            msg += "{}\n{}\n\n".format(feed_name, feed_addr)
        msg += (
            "```\nThe above feeds were extracted from\n{}"
            ).format(url)
        return msg
    elif feeds:
        feed_addr = await join_url(url, feeds[0].xpath('@href')[0])
        return [feed_addr]


async def feed_to_http(url):
    """
    Replace scheme feed by http.

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
    new_url = urlunsplit([
        "http",
        par_url.netloc,
        par_url.path,
        par_url.query,
        par_url.fragment
        ])
    return new_url


async def activitypub_to_http(namespace):
    """
    Replace ActivityPub namespace by http.

    Parameters
    ----------
    namespace : str
        Namespace.

    Returns
    -------
    new_url : str
        URL.
    """
    par_url = urlsplit(namespace)
    new_url = urlunsplit([
        "http",
        par_url.netloc,
        par_url.path,
        par_url.query,
        par_url.fragment
        ])
    return new_url
