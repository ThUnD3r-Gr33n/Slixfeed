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
