#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from slixfeed.config import get_value
from slixfeed.dt import current_time
from time import sleep
import logging


async def recover_connection(self, event, message):
    logging.warning(message)
    print(current_time(), message, "Attempting to reconnect.")
    self.connection_attempts += 1
    # if self.connection_attempts <= self.max_connection_attempts:
    #     self.reconnect(wait=5.0)  # wait a bit before attempting to reconnect
    # else:
    #     print(current_time(),"Maximum connection attempts exceeded.")
    #     logging.error("Maximum connection attempts exceeded.")
    print(current_time(), "Attempt number", self.connection_attempts)
    seconds = (get_value(
        "accounts", "XMPP Connect", "reconnect_timeout")) or 30
    seconds = int(seconds)
    print(current_time(), "Next attempt within", seconds, "seconds")
    # NOTE asyncio.sleep doesn't interval as expected
    # await asyncio.sleep(seconds)
    sleep(seconds)
    self.reconnect(wait=5.0)


async def inspect_connection(self, event):
    print("Disconnected\nReconnecting...")
    print(event)
    try:
        self.reconnect
    except:
        self.disconnect()
        print("Problem reconnecting")
