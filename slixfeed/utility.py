#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

TODO

1) is_feed: Look into the type ("atom", "rss2" etc.)

"""

from urllib.parse import urlsplit


def log_as_markdown(timestamp, filename, jid, message):
    """
    Log message to file.

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
    with open(filename + '.md', 'a') as file:
        # entry = "{} {}:\n{}\n\n".format(timestamp, jid, message)
        entry = (
        "## {}\n"
        "### {}\n\n"
        "{}\n\n").format(jid, timestamp, message)
        file.write(entry)


def get_title(url, feed):
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
    if not title:
        title = urlsplit(url).netloc
    return title


def is_feed(url, feed):
    """
    Determine whether document is feed or not.

    Parameters
    ----------
    url : str
        URL.
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
            msg = (
                "Empty feed for {}"
                ).format(url)
        except:
            val = False
            msg = (
            "No entries nor title for {}"
            ).format(url)
    elif feed.bozo:
        val = False
        msg = (
            "Bozo detected for {}"
            ).format(url)
    else:
        val = True
        msg = (
            "Good feed for {}"
            ).format(url)
    print(msg)
    return val
