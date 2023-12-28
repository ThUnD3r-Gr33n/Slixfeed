#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright © 2023 Schimon Jehudah
# This program is free software: you can redistribute it and/or modify
# it under the terms of the MIT License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# MIT License for more details.
#
# You should have received a copy of the MIT License along with
# this program.  If not, see <https://opensource.org/license/mit/>
#
# Slixfeed - RSS news bot for XMPP
#
# SPDX-FileCopyrightText: 2023 Schimon Jehudah
#
# SPDX-License-Identifier: MIT

from slixfeed.__main__ import Jabber
from slixfeed.xmpp.client import Slixfeed
from slixfeed.config import get_default_confdir
from argparse import ArgumentParser
import configparser
# import filehandler
# from filehandler import get_default_confdir
from getpass import getpass
import logging
import os
import sys

if __name__ == '__main__':

    # Setup the command line arguments.
    parser = ArgumentParser(description=Slixfeed.__doc__)

    # Output verbosity options.
    parser.add_argument(
         "-q",
         "--quiet",
         help="set logging to ERROR",
         action="store_const",
         dest="loglevel",
         const=logging.ERROR,
         default=logging.INFO
         )
    parser.add_argument(
        "-d",
        "--debug",
        help="set logging to DEBUG",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.INFO
        )

    # JID and password options.
    parser.add_argument(
        "-j",
        "--jid",
        dest="jid",
        help="Jabber ID"
        )
    parser.add_argument(
        "-p",
        "--password",
        dest="password",
        help="Password of JID"
        )
    parser.add_argument(
        "-n",
        "--nickname",
        dest="nickname",
        help="Display name"
        )

    args = parser.parse_args()

    # Setup logging.
    logging.basicConfig(
        level=args.loglevel,
        format='%(levelname)-8s %(message)s'
        )

    # Try configuration file
    config = configparser.RawConfigParser()
    config_dir = get_default_confdir()
    if not os.path.isdir(config_dir):
        os.mkdir(config_dir)
    # TODO Copy file from /etc/slixfeed/ or /usr/share/slixfeed/
    config_file = os.path.join(config_dir, r"accounts.ini")
    config.read(config_file)
    if config.has_section("XMPP"):
        xmpp = config["XMPP"]
        nickname = xmpp["nickname"]
        username = xmpp["username"]
        password = xmpp["password"]

    # Use arguments if were given
    if args.jid:
        username = args.jid
    if args.password:
        password = args.password
    if args.nickname:
        nickname = args.nickname

    # Prompt for credentials if none were given
    if username is None:
        username = input("Username: ")
    if password is None:
        password = getpass("Password: ")
    if nickname is None:
        nickname = input("Nickname: ")

    Jabber(username, password, nickname)
    sys.exit(0)
