#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

import sqlitehandler

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

# NOTE Perhaps this needs to be executed
# just once per program execution
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
    sqlitehandler.create_tables(db_file)
    # await sqlitehandler.set_default_values(db_file)
    if message:
        return await callback(db_file, message)
    else:
        return await callback(db_file)