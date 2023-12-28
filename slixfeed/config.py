#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

TODO

1) Use file settings.csv and pathnames.txt instead:
    See get_value_default and get_default_list

2) Website-specific filter (i.e. audiobookbay).

3) Exclude websites from filtering (e.g. metapedia).

4) Filter phrases:
    Refer to sqlitehandler.search_entries for implementation.
    It is expected to be more complex than function search_entries.

"""


import configparser
# from file import get_default_confdir
import slixfeed.config as config
import slixfeed.sqlite as sqlite
import os
from random import randrange
import sys
import yaml

async def get_value_default(key, section):
    """
    Get settings default value.

    Parameters
    ----------
    key : str
        Key: archive, enabled, interval, 
             length, old, quantum, random.

    Returns
    -------
    result : str
        Value.
    """
    config_res = configparser.RawConfigParser()
    config_dir = config.get_default_confdir()
    if not os.path.isdir(config_dir):
        config_dir = '/usr/share/slixfeed/'
    config_file = os.path.join(config_dir, r"settings.ini")
    config_res.read(config_file)
    if config_res.has_section(section):
        result = config_res[section][key]
    isinstance(result, int)
    isinstance(result, str)
    breakpoint
    return result


async def get_list(filename):
    """
    Get settings default value.

    Parameters
    ----------
    filename : str
        filename of yaml file.

    Returns
    -------
    result : list
        List of pathnames or keywords.
    """
    config_dir = config.get_default_confdir()
    if not os.path.isdir(config_dir):
        config_dir = '/usr/share/slixfeed/'
    config_file = os.path.join(config_dir, filename)
    with open(config_file) as defaults:
        # default = yaml.safe_load(defaults)
        # result = default[key]
        result = yaml.safe_load(defaults)
    return result


def get_default_dbdir():
    """
    Determine the directory path where dbfile will be stored.

    * If $XDG_DATA_HOME is defined, use it;
    * else if $HOME exists, use it;
    * else if the platform is Windows, use %APPDATA%;
    * else use the current directory.

    Returns
    -------
    str
        Path to database file.

    Note
    ----
    This function was taken from project buku.
    
    See https://github.com/jarun/buku

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

    * If $XDG_CONFIG_HOME is defined, use it;
    * else if $HOME exists, use it;
    * else if the platform is Windows, use %APPDATA%;
    * else use the current directory.

    Returns
    -------
    str
        Path to configueation directory.
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


async def initdb(jid, callback, message=None):
    """
    Callback function to instantiate action on database.

    Parameters
    ----------
    jid : str
        Jabber ID.
    callback : ?
        Function name.
    message : str, optional
        Optional kwarg when a message is a part or
        required argument. The default is None.

    Returns
    -------
    object
        Coroutine object.
    """
    db_dir = get_default_dbdir()
    if not os.path.isdir(db_dir):
        os.mkdir(db_dir)
    db_file = os.path.join(db_dir, r"{}.db".format(jid))
    sqlite.create_tables(db_file)
    # await set_default_values(db_file)
    if message:
        return await callback(db_file, message)
    else:
        return await callback(db_file)


async def add_to_list(newwords, keywords):
    """
    Append new keywords to list.

    Parameters
    ----------
    newwords : str
        List of new keywords.
    keywords : str
        List of current keywords.

    Returns
    -------
    val : str
        List of current keywords and new keywords.
    """
    if isinstance(keywords, str) or keywords is None:
        try:
            keywords = keywords.split(",")
        except:
            keywords = []
    newwords = newwords.lower().split(",")
    for word in newwords:
        word = word.strip()
        if len(word) and word not in keywords:
            keywords.extend([word])
    keywords.sort()
    val = ",".join(keywords)
    return val


async def remove_from_list(newwords, keywords):
    """
    Remove given keywords from list.

    Parameters
    ----------
    newwords : str
        List of new keywords.
    keywords : str
        List of current keywords.

    Returns
    -------
    val : str
        List of new keywords.
    """
    if isinstance(keywords, str) or keywords is None:
        try:
            keywords = keywords.split(",")
        except:
            keywords = []
    newwords = newwords.lower().split(",")
    for word in newwords:
        word = word.strip()
        if len(word) and word in keywords:
            keywords.remove(word)
    keywords.sort()
    val = ",".join(keywords)
    return val


async def is_listed(db_file, key, string):
    """
    Check keyword match.

    Parameters
    ----------
    db_file : str
        Path to database file.
    type : str
        "allow" or "deny".
    string : str
        String.

    Returns
    -------
    Matched keyword or None.

    """
# async def reject(db_file, string):
# async def is_blacklisted(db_file, string):
    list = await sqlite.get_filters_value(
        db_file,
        key
        )
    if list:
        list = list.split(",")
        for i in list:
            if not i or len(i) < 2:
                continue
            if i in string.lower():
                # print(">>> ACTIVATE", i)
                # return 1
                return i
    else:
        return None

"""

This code was tested at module datahandler

reject = 0
blacklist = await get_settings_value(
    db_file,
    "filter-deny"
    )
# print(">>> blacklist:")
# print(blacklist)
# breakpoint()
if blacklist:
    blacklist = blacklist.split(",")
    # print(">>> blacklist.split")
    # print(blacklist)
    # breakpoint()
    for i in blacklist:
        # print(">>> length", len(i))
        # breakpoint()
        # if len(i):
        if not i or len(i) < 2:
            print(">>> continue due to length", len(i))
            # breakpoint()
            continue
        # print(title)
        # print(">>> blacklisted word:", i)
        # breakpoint()
        test = (title + " " + summary + " " + link)
        if i in test.lower():
            reject = 1
            break
        
if reject:
    print("rejected:",title)
    entry = (title, '', link, source, date, 1);

"""
