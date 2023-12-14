#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

TODO

1) Use file settings.csv and pathnames.txt instead:
    See get_value_default and get_default_list

"""


import configparser
# from filehandler import get_default_confdir
import filehandler
import os
from random import randrange
import yaml

async def get_value_default(key):
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
    config = configparser.RawConfigParser()
    config_dir = filehandler.get_default_confdir()
    if not os.path.isdir(config_dir):
        config_dir = '/usr/share/slixfeed/'
    config_file = os.path.join(config_dir, r"settings.ini")
    config.read(config_file)
    if config.has_section("Settings"):
        result = config["Settings"][key]
    return result


async def get_list(key):
    """
    Get settings default value.

    Parameters
    ----------
    key : str
        Key: allow, deny, pathname, replace.

    Returns
    -------
    result : list
        List of pathnames or keywords.
    """
    config_dir = filehandler.get_default_confdir()
    if not os.path.isdir(config_dir):
        config_dir = '/usr/share/slixfeed/'
    config_file = os.path.join(config_dir, r"lists.yaml")
    with open(config_file) as defaults:
        default = yaml.safe_load(defaults)
        result = default[key]
    return result
