#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

FIXME

1) feed_mode_scan doesn't find feed for https://www.blender.org/
   even though it should be according to the pathnames dictionary.

TODO

1) Support Gemini and Gopher.

2) Check also for HTML, not only feed.bozo.

3) Add "if utility.is_feed(url, feed)" to view_entry and view_feed

4) Refactor view_entry and view_feed - Why "if" twice?

5) Replace sqlite.remove_nonexistent_entries by sqlite.check_entry_exist
   Same check, just reverse.

"""

from aiohttp import ClientError, ClientSession, ClientTimeout
from asyncio import TimeoutError
from asyncio.exceptions import IncompleteReadError
from bs4 import BeautifulSoup
from email.utils import parseaddr
from feedparser import parse
from http.client import IncompleteRead
from lxml import html
import slixfeed.config as config
from slixfeed.datetime import now, rfc2822_to_iso8601
import slixfeed.sqlite as sqlite
from slixfeed.url import complete_url, join_url, trim_url
from urllib import error
# from xml.etree.ElementTree import ElementTree, ParseError
from urllib.parse import urlsplit, urlunsplit


# async def dat():

# async def ftp():
    
# async def gemini():

# async def gopher():

# async def http():

# async def ipfs():

async def download_feed(url):
    """
    Download content of given URL.

    Parameters
    ----------
    url : list
        URL.

    Returns
    -------
    msg: list or str
        Document or error message.
    """
    user_agent = (
        config.get_value(
            "settings", "Network", "user-agent")
        ) or 'Slixfeed/0.1'
    headers = {'User-Agent': user_agent}
    proxy = (config.get_value(
        "settings", "Network", "http_proxy")) or ''
    timeout = ClientTimeout(total=10)
    async with ClientSession(headers=headers) as session:
    # async with ClientSession(trust_env=True) as session:
        try:
            async with session.get(url, proxy=proxy,
                                   # proxy_auth=(proxy_username, proxy_password),
                                   timeout=timeout
                                   ) as response:
                status = response.status
                if response.status == 200:
                    try:
                        doc = await response.text()
                        # print (response.content_type)
                        msg = [doc, status]
                    except:
                        # msg = [
                        #     False,
                        #     ("The content of this document "
                        #      "doesn't appear to be textual."
                        #      )
                        #     ]
                        msg = [
                            False, "Document is too large or is not textual."
                            ]
                else:
                    msg = [
                        False, "HTTP Error: " + str(status)
                        ]
        except ClientError as e:
            # print('Error', str(e))
            msg = [
                False, "Error: " + str(e)
                ]
        except TimeoutError as e:
            # print('Timeout:', str(e))
            msg = [
                False, "Timeout: " + str(e)
                ]
    return msg
