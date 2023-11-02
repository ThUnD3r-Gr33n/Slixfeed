#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from urllib.parse import urlparse

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