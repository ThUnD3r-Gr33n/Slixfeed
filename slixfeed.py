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

from argparse import ArgumentParser
from getpass import getpass
import logging
from slixfeed.__main__ import Jabber
from slixfeed.config import get_value
from slixfeed.xmpp.client import Slixfeed
import sys

# import socks
# import socket
# # socks.set_default_proxy(socks.SOCKS5, values[0], values[1])
# socks.set_default_proxy(socks.SOCKS5, 'localhost', 9050)
# socket.socket = socks.socksocket

if __name__ == '__main__':

    # Setup the command line arguments.
    parser = ArgumentParser(description=Slixfeed.__doc__)

    # Output verbosity options.
    parser.add_argument(
        "-q", "--quiet", help="set logging to ERROR",
        action="store_const", dest="loglevel",
        const=logging.ERROR, default=logging.INFO)
    parser.add_argument(
        "-d", "--debug", help="set logging to DEBUG",
        action="store_const", dest="loglevel",
        const=logging.DEBUG, default=logging.INFO)

    # JID and password options.
    parser.add_argument(
        "-j", "--jid", dest="jid", help="Jabber ID")
    parser.add_argument(
        "-p", "--password", dest="password", help="Password of JID")
    parser.add_argument(
        "-n", "--nickname", dest="nickname", help="Display name")

    args = parser.parse_args()

    # Setup logging.
    logging.basicConfig(
        level=args.loglevel, format='%(levelname)-8s %(message)s')

    # Try configuration file
    values = get_value(
        "accounts", "XMPP", ["nickname", "username", "password"])
    nickname = values[0]
    username = values[1]
    password = values[2]

    # Use arguments if were given
    if args.jid:
        username = args.jid
    if args.password:
        password = args.password
    if args.nickname:
        nickname = args.nickname

    # Prompt for credentials if none were given
    if not username:
        username = input("Username: ")
    if not password:
        password = getpass("Password: ")
    if not nickname:
        nickname = input("Nickname: ")

    Jabber(username, password, nickname)
    sys.exit(0)
