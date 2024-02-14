#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

NOTE

Accept symbols 🉑️ 👍️ ✍

TODO

Remove subscription from JID that do not (stopped) share presence.

"""

class XmppPresence:


    def send(self, jid, status_message, presence_type=None, status_type=None):
        self.send_presence(pto=jid,
                           pfrom=self.boundjid,
                           pshow=status_type,
                           pstatus=status_message,
                           ptype=presence_type)


    def subscription(self, jid, presence_type):
        self.send_presence_subscription(pto=jid,
                                        pfrom=self.boundjid.bare,
                                        ptype=presence_type,
                                        pnick=self.alias)
