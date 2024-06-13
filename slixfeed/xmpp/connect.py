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
from slixfeed.dt import current_time
from slixfeed.log import Logger
from slixmpp.exceptions import IqTimeout, IqError
from time import sleep

logger = Logger(__name__)


class XmppConnect:


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
        jid_from = str(self.boundjid) if self.is_component else None
        if not jid:
            jid = self.boundjid.bare
        while True:
            rtt = None
            try:
                rtt = await self['xep_0199'].ping(jid,
                                                  ifrom=jid_from,
                                                  timeout=10)
                logger.info('Success! RTT: %s', rtt)
            except IqError as e:
                logger.error('Error pinging %s: %s', jid,
                              e.iq['error']['condition'])
            except IqTimeout:
                logger.warning('No response from %s', jid)
            if not rtt:
                logger.warning('Disconnecting...')
                self.disconnect()
                break
            await asyncio.sleep(60 * 1)


    def recover(self, message):
        logger.warning(message)
        print(current_time(), message, 'Attempting to reconnect.')
        self.connection_attempts += 1
        # if self.connection_attempts <= self.max_connection_attempts:
        #     self.reconnect(wait=5.0)  # wait a bit before attempting to reconnect
        # else:
        #     print(current_time(),"Maximum connection attempts exceeded.")
        #     logging.error("Maximum connection attempts exceeded.")
        print(current_time(), 'Attempt number', self.connection_attempts)
        seconds = self.reconnect_timeout or 30
        seconds = int(seconds)
        print(current_time(), 'Next attempt within', seconds, 'seconds')
        # NOTE asyncio.sleep doesn't interval as expected
        # await asyncio.sleep(seconds)
        sleep(seconds)
        self.reconnect(wait=5.0)


    def inspect(self):
        print('Disconnected\nReconnecting...')
        try:
            self.reconnect
        except:
            self.disconnect()
            print('Problem reconnecting')


class XmppConnectTask:


    def ping(self):
        try:
            self.task_ping_instance.cancel()
        except:
            logger.info('No ping task to cancel.')
        self.task_ping_instance = asyncio.create_task(XmppConnect.ping(self))
