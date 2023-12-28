#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from slixfeed.datetime import current_time
from time import sleep


async def recover_connection(self, event):
    self.connection_attempts += 1
    # if self.connection_attempts <= self.max_connection_attempts:
    #     self.reconnect(wait=5.0)  # wait a bit before attempting to reconnect
    # else:
    #     print(current_time(),"Maximum connection attempts exceeded.")
    #     logging.error("Maximum connection attempts exceeded.")
    print(current_time(), "Attempt number", self.connection_attempts)
    seconds = 30
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
