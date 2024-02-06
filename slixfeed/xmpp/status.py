#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from slixfeed.xmpp.utility import get_chat_type


class XmppStatus:


    async def send(self, jid, status_message, status_type=None, chat_type=None):
        if not chat_type:
            chat_type = await get_chat_type(self, jid)
        self.send_presence(
            pto=jid,
            pfrom=self.boundjid.bare,
            pshow=status_type,
            pstatus=status_message,
            ptype=chat_type
            )
