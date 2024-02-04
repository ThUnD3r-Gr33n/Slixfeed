#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def send(self, jid, status_message, status_type=None):
    self.send_presence(
        pshow=status_type,
        pstatus=status_message,
        pfrom=self.boundjid.bare,
        pto=jid
        )
