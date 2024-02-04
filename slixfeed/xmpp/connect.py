#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

TODO

1) Check interval, and if no connection is establish after 30 seconds
   then disconnect and reconnect again.

2) or Check ping, and if no ping is received after 30 seconds then
   disconnect and try to reconnect again.

"""

import asyncio
from slixfeed.config import get_value
from slixfeed.dt import current_time
from slixmpp.exceptions import IqTimeout, IqError
from time import sleep
import logging


async def ping(self, jid=None):
    """
    Check for ping and disconnect if no ping has been received.

    Parameters
    ----------
    jid : str, optional
        Jabber ID. The default is None.

    Returns
    -------
    None.

    """
    if not jid:
        jid = self.boundjid.bare
    while True:
        rtt = None
        try:
            rtt = await self['xep_0199'].ping(jid, timeout=10)
            logging.info("Success! RTT: %s", rtt)
        except IqError as e:
            logging.info("Error pinging %s: %s",
                         jid,
                         e.iq['error']['condition'])
        except IqTimeout:
            logging.info("No response from %s", jid)
        if not rtt:
            self.disconnect()
        await asyncio.sleep(60 * 1)


async def recover_connection(self, message):
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
        "accounts", "XMPP", "reconnect_timeout")) or 30
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
