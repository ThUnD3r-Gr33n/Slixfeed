#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

TODO

1) Website-specific filter (i.e. audiobookbay).

2) Exclude websites from being subjected to filtering (e.g. metapedia).

3) Filter phrases:
    Refer to sqlitehandler.search_entries for implementation.
    It is expected to be more complex than function search_entries.

4) Copy file from /etc/slixfeed/ or /usr/share/slixfeed/

5) Merge get_value_default into get_value.

6) Use TOML https://ruudvanasseldonk.com/2023/01/11/the-yaml-document-from-hell

7) Make the program portable (directly use the directory assets) -- Thorsten

7.1) Read missing files from base directories or either set error message.

"""

import configparser
import logging
import os
# from random import randrange
import slixfeed.sqlite as sqlite
import sys
import tomli_w
try:
    import tomllib
except:
    import tomli as tomllib


async def set_setting_value(db_file, key, val):
    key = key.lower()
    if sqlite.is_setting_key(db_file, key):
        await sqlite.update_setting_value(db_file, [key, val])
    else:
        await sqlite.set_setting_value(db_file, [key, val])


def get_setting_value(db_file, key):
    value = sqlite.get_setting_value(db_file, key)
    if value:
        value = value[0]
    else:
        value = get_value("settings", "Settings", key)
    try:
        value = int(value)
    except ValueError as e:
        print('ValueError for value {} (key {}):\n{}'.format(value, key, e))
        if isinstance(value, bool):
            if value:
                value = 1
            else:
                value = 0
    return value


# TODO Merge with backup_obsolete
def update_proxies(file, proxy_name, proxy_type, proxy_url, action='remove'):
    """
    Add given URL to given list.

    Parameters
    ----------
    file : str
        Filename.
    proxy_name : str
        Proxy name.
    proxy_type : str
        Proxy title.
    proxy_url : str
        Proxy URL.
    action : str
        add or remove

    Returns
    -------
    None.
    """
    data = open_config_file('proxies.toml')
    proxy_list = data['proxies'][proxy_name][proxy_type]
    proxy_index = proxy_list.index(proxy_url)
    proxy_list.pop(proxy_index)
    with open(file, 'w') as new_file:
        content = tomli_w.dumps(data)
        new_file.write(content)


# TODO Merge with update_proxies
def backup_obsolete(file, proxy_name, proxy_type, proxy_url, action='add'):
    """
    Add given URL to given list.

    Parameters
    ----------
    file : str
        Filename.
    proxy_name : str
        Proxy name.
    proxy_type : str
        Proxy title.
    proxy_url : str
        Proxy URL.
    action : str
        add or remove

    Returns
    -------
    None.
    """
    data = open_config_file('proxies_obsolete.toml')
    proxy_list = data['proxies'][proxy_name][proxy_type]
    proxy_list.extend([proxy_url])
    with open(file, 'w') as new_file:
        content = tomli_w.dumps(data)
        new_file.write(content)


def create_skeleton(file):
    with open(file, 'rb') as original_file:
        data = tomllib.load(original_file)
    data = clear_values(data)
    with open('proxies_obsolete.toml', 'w') as new_file:
        content = tomli_w.dumps(data)
        new_file.write(content)


def clear_values(input):
    if isinstance(input, dict):
        return {k: clear_values(v) for k, v in input.items()}
    elif isinstance(input, list):
        return ['']
    else:
        return ''


# TODO Return dict instead of list
def get_value(filename, section, keys):
    """
    Get setting value.

    Parameters
    ----------
    filename : str
        INI filename.
    keys : list or str
        A single key as string or multiple keys as list.
    section : str
        INI Section.

    Returns
    -------
    result : list or str
        A single value as string or multiple values as list.
    """
    result = None
    config_res = configparser.RawConfigParser()
    config_dir = get_default_config_directory()
    if not os.path.isdir(config_dir):
        config_dir = '/usr/share/slixfeed/'
    if not os.path.isdir(config_dir):
        config_dir = os.path.dirname(__file__) + "/assets"
    config_file = os.path.join(config_dir, filename + ".ini")
    config_res.read(config_file)
    if config_res.has_section(section):
        section_res = config_res[section]
        if isinstance(keys, list):
            result = []
            for key in keys:
                if key in section_res:
                    value = section_res[key]
                    logging.debug(
                        "Found value {} for key {}".format(value, key)
                        )
                else:
                    value = ''
                    logging.debug("Missing key:", key)
                result.extend([value])
        elif isinstance(keys, str):
            key = keys
            if key in section_res:
                result = section_res[key]
                logging.debug(
                    "Found value {} for key {}".format(result, key)
                    )
            else:
                result = ''
                # logging.error("Missing key:", key)
    if result == None:
        logging.error(
            "Check configuration file {}.ini for "
            "missing key(s) \"{}\" under section [{}].".format(
                filename, keys, section)
            )
    else:
        return result


# TODO Store config file as an object in runtime, otherwise
# the file will be opened time and time again.
# TODO Copy file from /etc/slixfeed/ or /usr/share/slixfeed/
def get_value_default(filename, section, key):
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
    config_dir = get_default_config_directory()
    if not os.path.isdir(config_dir):
        config_dir = '/usr/share/slixfeed/'
    config_file = os.path.join(config_dir, filename + ".ini")
    config_res.read(config_file)
    if config_res.has_section(section):
        result = config_res[section][key]
    return result


# TODO DELETE THIS FUNCTION OR KEEP ONLY THE CODE BELOW NOTE
# IF CODE BELOW NOTE IS KEPT, RENAME FUNCTION TO open_toml
def open_config_file(filename):
    """
    Get settings default value.

    Parameters
    ----------
    filename : str
        Filename of toml file.

    Returns
    -------
    result : list
        List of pathnames or keywords.
    """
    config_dir = get_default_config_directory()
    if not os.path.isdir(config_dir):
        config_dir = '/usr/share/slixfeed/'
    if not os.path.isdir(config_dir):
        config_dir = os.path.dirname(__file__) + "/assets"
    config_file = os.path.join(config_dir, filename)
    # NOTE THIS IS THE IMPORTANT CODE
    with open(config_file, mode="rb") as defaults:
        # default = yaml.safe_load(defaults)
        # result = default[key]
        result = tomllib.load(defaults)
    return result


def get_default_data_directory():
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
                    return os.path.abspath('.slixfeed/data')
            else:
                return os.path.abspath('.slixfeed/data')
        else:
            data_home = os.path.join(
                os.environ.get('HOME'), '.local', 'share'
                )
    return os.path.join(data_home, 'slixfeed')


def get_default_cache_directory():
    """
    Determine the directory path where dbfile will be stored.

    * If $XDG_DATA_HOME is defined, use it;
    * else if $HOME exists, use it;
    * else if the platform is Windows, use %APPDATA%;
    * else use the current directory.

    Returns
    -------
    str
        Path to cache directory.
    """
#    data_home = xdg.BaseDirectory.xdg_data_home
    data_home = os.environ.get('XDG_CACHE_HOME')
    if data_home is None:
        if os.environ.get('HOME') is None:
            if sys.platform == 'win32':
                data_home = os.environ.get('APPDATA')
                if data_home is None:
                    return os.path.abspath('.slixfeed/cache')
            else:
                return os.path.abspath('.slixfeed/cache')
        else:
            data_home = os.path.join(
                os.environ.get('HOME'), '.cache'
                )
    return os.path.join(data_home, 'slixfeed')


# TODO Write a similar function for file.
# NOTE the is a function of directory, noot file.
def get_default_config_directory():
    """
    Determine the directory path where configuration will be stored.

    * If $XDG_CONFIG_HOME is defined, use it;
    * else if $HOME exists, use it;
    * else if the platform is Windows, use %APPDATA%;
    * else use the current directory.

    Returns
    -------
    str
        Path to configuration directory.
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
            config_home = os.path.join(
                os.environ.get('HOME'), '.config'
                )
    return os.path.join(config_home, 'slixfeed')


def get_pathname_to_database(jid_file):
    """
    Callback function to instantiate action on database.

    Parameters
    ----------
    jid_file : str
        Filename.
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
    db_dir = get_default_data_directory()
    if not os.path.isdir(db_dir):
        os.mkdir(db_dir)
    if not os.path.isdir(db_dir + "/sqlite"):
        os.mkdir(db_dir + "/sqlite")
    db_file = os.path.join(db_dir, "sqlite", r"{}.db".format(jid_file))
    sqlite.create_tables(db_file)
    return db_file
    # await set_default_values(db_file)
    # if message:
    #     return await callback(db_file, message)
    # else:
    #     return await callback(db_file)


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


def is_include_keyword(db_file, key, string):
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
    keywords = sqlite.get_filter_value(db_file, key)
    keywords = keywords[0] if keywords else ''
    keywords = keywords.split(",")
    keywords = keywords + (open_config_file("lists.toml")[key])
    for keyword in keywords:
        if not keyword or len(keyword) < 2:
            continue
        if keyword in string.lower():
            # print(">>> ACTIVATE", i)
            # return 1
            return keyword

"""

This code was tested at module datahandler

reject = 0
blacklist = sqlite.get_setting_value(
    db_file,
    "deny"
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
