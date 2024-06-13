#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from slixfeed.log import Logger
from slixmpp.exceptions import IqError, IqTimeout

logger = Logger(__name__)

class XmppIQ:

    async def send(self, iq):
        try:
            await iq.send(timeout=15)
        except IqTimeout as e:
            logger.error('Error Timeout')
            logger.error(str(e))
        except IqError as e:
            logger.error('Error XmppIQ')
            logger.error(str(e))
