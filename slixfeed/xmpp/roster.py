#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

TODO

1) remove_subscription (clean_roster)
   Remove presence from contacts that don't share presence.

"""

import slixfeed.xmpp.utility as utility

async def remove(self, jid):
    """
    Remove JID to roster.

    Parameters
    ----------
    jid : str
        Jabber ID.

    Returns
    -------
    None.
    """
    self.update_roster(
        jid,
        subscription="remove"
        )


async def add(self, jid):
    """
    Add JID to roster.

    Parameters
    ----------
    jid : str
        Jabber ID.

    Returns
    -------
    None.
    """
    if await utility.jid_type(self, jid) == "groupchat":
        # Check whether JID is in bookmarks; otherwise, add it.
        print(jid, "is muc")
        return
    else:
        await self.get_roster()
        # Check whether JID is in roster; otherwise, add it.
        if jid not in self.client_roster.keys():
            self.send_presence_subscription(
                pto=jid,
                pfrom=self.boundjid.bare,
                ptype="subscribe",
                pnick=self.alias
                )
            self.update_roster(
                jid,
                subscription="both"
                )


def remove_subscription(self):
    """
    Remove subscription from contacts that don't share their presence.

    Returns
    -------
    None.
    """