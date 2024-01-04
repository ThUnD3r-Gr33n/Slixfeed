#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

TODO

1) is_feed: Look into the type ("atom", "rss2" etc.)

"""


def title(feed):
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
        Title or None.
    """
    try:
        title = feed["feed"]["title"]
    except:
        title = None
    return title


def is_feed(feed):
    """
    Determine whether document is feed or not.

    Parameters
    ----------
    feed : dict
        Parsed feed.

    Returns
    -------
    val : boolean
        True or False.
    """
    msg = None
    if not feed.entries:
        try:
            feed["feed"]["title"]
            val = True
            # msg = (
            #     "Empty feed for {}"
            #     ).format(url)
        except:
            val = False
            # msg = (
            #     "No entries nor title for {}"
            #     ).format(url)
    elif feed.bozo:
        val = False
        # msg = (
        #     "Bozo detected for {}"
        #     ).format(url)
    else:
        val = True
        # msg = (
        #     "Good feed for {}"
        #     ).format(url)
    print(msg)
    return val
