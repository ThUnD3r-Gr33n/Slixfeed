#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from slixmpp.exceptions import IqError

class XmppIQ:

    async def send(self, iq):
        try:
            await iq.send(timeout=5)
        except IqError as e:
            if e.etype == 'cancel' and e.condition == 'conflict':
                return
            raise
