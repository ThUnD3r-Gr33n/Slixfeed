#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

def get_default_dbdir():
    """
    Determine the directory path where dbfile will be stored.

    If $XDG_DATA_HOME is defined, use it
    else if $HOME exists, use it
    else if the platform is Windows, use %APPDATA%
    else use the current directory.

    :return: Path to database file.

    Note
    ----
    This code was taken from the buku project.

    * Arun Prakash Jana (jarun)
    * Dmitry Marakasov (AMDmi3)
    """
#    data_home = xdg.BaseDirectory.xdg_data_home
    data_home = os.environ.get('XDG_DATA_HOME')
    if data_home is None:
        if os.environ.get('HOME') is None:
            if sys.platform == 'win32':
                data_home = os.environ.get('APPDATA')
                if data_home is None:
                    return os.path.abspath('.')
            else:
                return os.path.abspath('.')
        else:
            data_home = os.path.join(os.environ.get('HOME'), '.local', 'share')
    return os.path.join(data_home, 'slixfeed')


def get_default_confdir():
    """
    Determine the directory path where configuration will be stored.

    If $XDG_CONFIG_HOME is defined, use it
    else if $HOME exists, use it
    else if the platform is Windows, use %APPDATA%
    else use the current directory.

    :return: Path to configueation directory.
    """
#    config_home = xdg.BaseDirectory.xdg_config_home
    config_home = os.environ.get('XDG_CONFIG_HOME')
    if config_home is None:
        if os.environ.get('HOME') is None:
            if sys.platform == 'win32':
                config_home = os.environ.get('APPDATA')
                if config_home is None:
                    return os.path.abspath('.')
            else:
                return os.path.abspath('.')
        else:
            config_home = os.path.join(os.environ.get('HOME'), '.config')
    return os.path.join(config_home, 'slixfeed')


async def get_value_default(key):
    """
    Get settings default value.

    :param key: "enabled", "interval", "quantum".
    :return: Integer.
    """
    if key == "enabled":
        result = 1
    elif key == "quantum":
        result = 4
    elif key == "interval":
        result = 30
    return result


# async def generate_dictionary():
def get_default_list():
    """
    Generate a dictionary file.

    :return: List.
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
