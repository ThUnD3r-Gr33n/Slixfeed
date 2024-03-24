#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from slixmpp.exceptions import IqError, IqTimeout

class XmppIQ:

    async def send(self, iq):
        try:
            await iq.send(timeout=5)
        except (IqError, IqTimeout) as e:
            logging.error('Error XmppIQ')
            logging.error(str(e))
