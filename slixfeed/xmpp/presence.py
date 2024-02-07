#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

NOTE

Accept symbols 🉑️ 👍️ ✍

"""

class XmppPresence:


    def send(self, jid, status_message, presence_type=None, status_type=None):
        self.send_presence(pto=jid,
                           pfrom=self.boundjid.bare,
                           pshow=status_type,
                           pstatus=status_message,
                           ptype=presence_type)


    def subscribe(self, jid):
        self.send_presence_subscription(pto=jid,
                                        pfrom=self.boundjid.bare,
                                        ptype='subscribe',
                                        pnick=self.alias)


    def remove(self):
        """
        Remove subscription from JID that do not (stopped) share presence.

        Returns
        -------
        None.
        """
