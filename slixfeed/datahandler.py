#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import feedparser
import aiohttp
import asyncio
import os
import sqlitehandler
import confighandler

from http.client import IncompleteRead
from asyncio.exceptions import IncompleteReadError
from urllib import error
from bs4 import BeautifulSoup
# from xml.etree.ElementTree import ElementTree, ParseError
from urllib.parse import urlparse
from lxml import html

async def download_updates(db_file):
    """
    Check feeds for new entries.

    :param db_file: Database filename.
    """
    urls = await sqlitehandler.get_subscriptions(db_file)

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
        
        await sqlitehandler.update_source_status(db_file, res[1], source)

        if res[0]:
            try:
                feed = feedparser.parse(res[0])
                if feed.bozo:
                    # bozo = ("WARNING: Bozo detected for feed <{}>. "
                    #         "For more information, visit "
                    #         "https://pythonhosted.org/feedparser/bozo.html"
                    #         .format(source))
                    # print(bozo)
                    valid = 0
                else:
                    valid = 1
                await sqlitehandler.update_source_validity(db_file, source, valid)
            except (IncompleteReadError, IncompleteRead, error.URLError) as e:
                print(e)
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
            await sqlitehandler.remove_nonexistent_entries(db_file, feed, source)

            new_entry = 0
            for entry in entries:

                if entry.has_key("title"):
                    title = entry.title
                else:
                    title = feed["feed"]["title"]

                if entry.has_key("link"):
                    link = entry.link
                else:
                    link = source

                exist = await sqlitehandler.check_entry_exist(db_file, title, link)

                if not exist:
                    new_entry = new_entry + 1
                    # TODO Enhance summary
                    if entry.has_key("summary"):
                        summary = entry.summary
                        # Remove HTML tags
                        summary = BeautifulSoup(summary, "lxml").text
                        # TODO Limit text length
                        summary = summary.replace("\n\n", "\n")[:300] + "  ‍⃨"
                    else:
                        summary = '*** No summary ***'
                    entry = (title, summary, link, source, 0);
                    await sqlitehandler.add_entry_and_set_date(db_file, source, entry)


async def add_feed(db_file, url):
    """
    Check whether feed exist, otherwise process it.

    :param db_file: Database filename.
    :param url: URL.
    :return: Status message.
    """
    exist = await sqlitehandler.check_feed_exist(db_file, url)
    
    if not exist:
        res = await download_feed(url)
        if res[0]:
            feed = feedparser.parse(res[0])
            title = await get_title(url, feed)
            if feed.bozo:
                bozo = ("WARNING: Bozo detected. Failed to load <{}>.".format(url))
                print(bozo)
                try:
                    # tree = etree.fromstring(res[0]) # etree is for xml
                    tree = html.fromstring(res[0])
                except:
                    return "Failed to parse URL <{}> as feed".format(url)

                print("RSS Auto-Discovery Engaged")
                xpath_query = """//link[(@rel="alternate") and (@type="application/atom+xml" or @type="application/rdf+xml" or @type="application/rss+xml")]"""
                # xpath_query = """//link[(@rel="alternate") and (@type="application/atom+xml" or @type="application/rdf+xml" or @type="application/rss+xml")]/@href"""
                # xpath_query = "//link[@rel='alternate' and @type='application/atom+xml' or @rel='alternate' and @type='application/rss+xml' or @rel='alternate' and @type='application/rdf+xml']/@href"
                feeds = tree.xpath(xpath_query)
                if len(feeds) > 1:
                    msg = "RSS Auto-Discovery has found {} feeds:\n\n".format(len(feeds))
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
                        feed_addr = feed.xpath('@href')[0]
                        msg += "{}\n{}\n\n".format(feed_name, feed_addr)
                    msg += "The above feeds were extracted from\n{}".format(url)
                    return msg
                elif feeds:
                    url = feeds[0].xpath('@href')[0]
                    # Why wouldn't add_feed return a message
                    # upon success unless return is explicitly
                    # mentioned, yet upon failure it wouldn't?
                    return await add_feed(db_file, url)

                print("RSS Scan Mode Engaged")
                feeds = {}
                paths = []
                # TODO Test
                cfg_dir = confighandler.get_default_confdir()
                if not os.path.isdir(cfg_dir):
                    os.mkdir(cfg_dir)
                cfg_file = os.path.join(cfg_dir, r"url_paths.txt")
                if not os.path.isfile(cfg_file):
                    # confighandler.generate_dictionary()
                    list = confighandler.get_default_list()
                    file = open(cfg_file, "w")
                    file.writelines("\n".join(list))
                    file.close()
                file = open(cfg_file, "r")
                lines = file.readlines()
                for line in lines:
                    paths.extend([line.strip()])
                for path in paths:
                    # xpath_query = "//*[@*[contains(.,'{}')]]".format(path)
                    xpath_query = "//a[contains(@href,'{}')]".format(path)
                    addresses = tree.xpath(xpath_query)
                    parted_url = urlparse(url)
                    # NOTE Should number of addresses be limited or
                    # perhaps be N from the start and N from the end
                    for address in addresses:
                        address = address.xpath('@href')[0]
                        if address.startswith('/'):
                            address = parted_url.scheme + '://' + parted_url.netloc + address
                        res = await download_feed(address)
                        if res[1] == 200:
                            try:
                                feeds[address] = feedparser.parse(res[0])["feed"]["title"]
                            except:
                                continue
                if len(feeds) > 1:
                    msg = "RSS URL scan has found {} feeds:\n\n".format(len(feeds))
                    for feed in feeds:
                        # try:
                        #     res = await download_feed(feed)
                        # except:
                        #     continue
                        feed_name = feeds[feed]
                        feed_addr = feed
                        msg += "{}\n{}\n\n".format(feed_name, feed_addr)
                    msg += "The above feeds were extracted from\n{}".format(url)
                    return msg
                elif feeds:
                    url = list(feeds)[0]
                    return await add_feed(db_file, url)

                # (HTTP) Request(s) Paths
                print("RSS Arbitrary Mode Engaged")
                feeds = {}
                parted_url = urlparse(url)
                for path in paths:
                    address = parted_url.scheme + '://' + parted_url.netloc + path
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
                        paths.extend([".atom", ".feed", ".rdf", ".rss"]) if '.rss' not in paths else -1
                        # if paths.index('.rss'):
                        #     paths.extend([".atom", ".feed", ".rdf", ".rss"])
                        address = parted_url.scheme + '://' + parted_url.netloc + '/' + parted_url.path.split('/')[1] + path
                        res = await download_feed(address)
                        if res[1] == 200:
                            try:
                                title = feedparser.parse(res[0])["feed"]["title"]
                            except:
                                title = '*** No Title ***'
                            feeds[address] = title
                if len(feeds) > 1:
                    msg = "RSS URL discovery has found {} feeds:\n\n".format(len(feeds))
                    for feed in feeds:
                        feed_name = feeds[feed]
                        feed_addr = feed
                        msg += "{}\n{}\n\n".format(feed_name, feed_addr)
                    msg += "The above feeds were extracted from\n{}".format(url)
                elif feeds:
                    url = list(feeds)[0]
                    msg = await add_feed(db_file, url)
                else:
                    msg = "No news feeds were found for URL <{}>.".format(url)
            else:
                msg = await sqlitehandler.add_feed(db_file, title, url, res)
        else:
            msg = "Failed to get URL <{}>.  Reason: {}".format(url, res[1])
    else:
        ix = exist[0]
        name = exist[1]
        msg = "> {}\nNews source \"{}\" is already listed in the subscription list at index {}".format(url, name, ix)
    return msg


async def download_feed(url):
    """
    Download content of given URL.

    :param url: URL.
    :return: Document or error message.
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
                        return [doc, status]
                    except:
                        # return [False, "The content of this document doesn't appear to be textual."]
                        return [False, "Document is too large or is not textual."]
                else:
                    return [False, "HTTP Error: " + str(status)]
        except aiohttp.ClientError as e:
            print('Error', str(e))
            return [False, "Error: " + str(e)]
        except asyncio.TimeoutError as e:
            # print('Timeout:', str(e))
            return [False, "Timeout: " + str(e)]


async def get_title(url, feed):
    """
    Get title of feed.

    :param url: URL
    :param feed: Parsed feed
    :return: Title or URL hostname.
    """
    try:
        title = feed["feed"]["title"]
    except:
        title = urlparse(url).netloc
    return title
