#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

TODO

1) Use file settings.csv and pathnames.txt instead:
    See get_value_default and get_default_list

"""

import os
import filehandler


async def get_value_default(key):
    """
    Get settings default value.

    Parameters
    ----------
    key : str
        Key: enabled, filter-allow, filter-deny,
             interval, quantum, random.

    Returns
    -------
    result : int or str
        Value.
    """
    match key:
        case "enabled":
            result = 1
        case "filter-allow":
            result = "hitler,sadam,saddam"
        case "filter-deny":
            result = "crim,dead,death,disaster,murder,war"
        case "interval":
            result = 300
        case "quantum":
            result = 3
        case "random":
            result = 0
        case "read":
            result = "https://www.blacklistednews.com/rss.php"
    return result


def get_list():
    """
    Get dictionary file.

    Returns
    -------
    paths : list
        Dictionary of pathnames.
    """
    paths = []
    cfg_dir = filehandler.get_default_confdir()
    if not os.path.isdir(cfg_dir):
        os.mkdir(cfg_dir)
    cfg_file = os.path.join(cfg_dir, r"url_paths.txt")
    if not os.path.isfile(cfg_file):
        # confighandler.generate_dictionary()
        list = get_default_list()
        file = open(cfg_file, "w")
        file.writelines("\n".join(list))
        file.close()
    file = open(cfg_file, "r")
    lines = file.readlines()
    for line in lines:
        paths.extend([line.strip()])
    return paths


# async def generate_dictionary():
def get_default_list():
    """
    Generate a dictionary file.

    Returns
    -------
    paths : list
        Dictionary of pathnames.
    """
    paths = [
        ".atom",
        ".rss",
        ".xml",
        "/?feed=atom",
        "/?feed=rdf",
        "/?feed=rss",
        "/?feed=xml", # wordpress
        "/?format=atom",
        "/?format=rdf",
        "/?format=rss",
        "/?format=xml", # phpbb
        "/app.php/feed",
        "/atom",
        "/atom.php",
        "/atom.xml",
        "/blog/feed/",
        "/content-feeds/",
        "/external.php?type=RSS2",
        "/en/feed/",
        "/feed", # good practice
        "/feed.atom",
        # "/feed.json",
        "/feed.php",
        "/feed.rdf",
        "/feed.rss",
        "/feed.xml",
        "/feed/atom/",
        "/feeds/news_feed",
        "/feeds/posts/default",
        "/feeds/posts/default?alt=atom",
        "/feeds/posts/default?alt=rss",
        "/feeds/rss/news.xml.php",
        "/forum_rss.php",
        "/index.atom",
        "/index.php/feed",
        "/index.php?type=atom;action=.xml", #smf
        "/index.php?type=rss;action=.xml", #smf
        "/index.rss",
        "/jekyll/feed.xml",
        "/latest.rss",
        "/news",
        "/news.xml",
        "/news.xml.php",
        "/news/feed",
        "/posts.rss", # discourse
        "/rdf",
        "/rdf.php",
        "/rdf.xml",
        "/rss",
        # "/rss.json",
        "/rss.php",
        "/rss.xml",
        "/syndication.php?type=atom1.0", #mybb
        "/syndication.php?type=rss2.0",
        "/timeline.rss",
        "/videos.atom",
        # "/videos.json",
        "/videos.xml",
        "/xml/feed.rss"
        ]
    return paths
    # cfg_dir = get_default_confdir()
    # if not os.path.isdir(cfg_dir):
    #     os.mkdir(cfg_dir)
    # cfg_file = os.path.join(cfg_dir, r"url_paths.txt")
    # if not os.path.isfile(cfg_file):
    #     file = open(cfg_file, "w")
    #     file.writelines("\n".join(paths))
    #     file.close()
