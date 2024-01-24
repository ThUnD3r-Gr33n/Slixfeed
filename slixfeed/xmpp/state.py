#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from slixmpp.xmlstream.matcher import MatchXPath
from slixmpp.xmlstream.handler import Callback
from slixmpp.xmlstream import ET

async def request(self, jid):
    """
    Ask contant to settle subscription.

    Parameters
    ----------
    jid : str
        Jabber ID.

    Returns
    -------
    None.
    """
    # Check whether JID is subscribed; otherwise, ask for presence.
    if self.is_component:
        presence_probe = ET.Element('presence')
        presence_probe.attrib['type'] = 'probe'
        presence_probe.attrib['to'] = jid
        print(presence_probe)
        breakpoint()
        self.send_raw(str(presence_probe))
        presence_probe.send()
    else:
        if not self.client_roster[jid]["to"]:
            self.send_presence_subscription(
                pto=jid,
                pfrom=self.boundjid.bare,
                ptype="subscribe",
                pnick=self.alias
                )
            self.send_message(
                mto=jid,
                mfrom=self.boundjid.bare,
                # mtype="headline",
                msubject="RSS News Bot",
                mbody=(
                    "Share online status to receive updates."
                    ),
                mnick=self.alias
                )
            self.send_presence(
                pto=jid,
                pfrom=self.boundjid.bare,
                # Accept symbol 🉑️ 👍️ ✍
                pstatus=(
                    "✒️ Share online status to receive updates."
                    ),
                # ptype="subscribe",
                pnick=self.alias
                )


async def unsubscribed(self, presence):
    jid = presence["from"].bare
    self.send_message(
        mto=jid,
        mfrom=self.boundjid.bare,
        mbody="You have been unsubscribed."
        )
    self.send_presence(
        pto=jid,
        pfrom=self.boundjid.bare,
        pstatus="🖋️ Subscribe to receive updates",
        pnick=self.alias
        )
