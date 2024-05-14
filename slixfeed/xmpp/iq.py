#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from slixmpp.exceptions import IqError, IqTimeout

class XmppIQ:

    async def send(self, iq):
        try:
            await iq.send(timeout=15)
        except IqTimeout as e:
            logging.error('Error Timeout')
            logging.error(str(e))
        except IqError as e:
            logging.error('Error XmppIQ')
            logging.error(str(e))
