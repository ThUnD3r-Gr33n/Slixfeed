#!/usr/bin/env python3
# -*- coding: utf-8 -*-


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
    if not self.client_roster[jid]["to"]:
        self.send_presence_subscription(
            pto=jid,
            pfrom=self.boundjid.bare,
            ptype="subscribe",
            pnick=self.nick
            )
        self.send_message(
            mto=jid,
            # mtype="headline",
            msubject="RSS News Bot",
            mbody=(
                "Share online status to receive updates."
                ),
            mfrom=self.boundjid.bare,
            mnick=self.nick
            )
        self.send_presence(
            pto=jid,
            pfrom=self.boundjid.bare,
            # Accept symbol 🉑️ 👍️ ✍
            pstatus=(
                "✒️ Share online status to receive updates."
                ),
            # ptype="subscribe",
            pnick=self.nick
            )


async def unsubscribed(self, presence):
    jid = presence["from"].bare
    self.send_message(
        mto=jid,
        mbody="You have been unsubscribed."
        )
    self.send_presence(
        pto=jid,
        pfrom=self.boundjid.bare,
        pstatus="🖋️ Subscribe to receive updates",
        pnick=self.nick
        )
    self.update_roster(
        jid,
        subscription="remove"
        )
