#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from slixmpp.exceptions import IqTimeout
import logging

async def jid_type(self, jid):
    """
    Check whether a JID is of MUC.

    Parameters
    ----------
    jid : str
        Jabber ID.

    Returns
    -------
    str
        "chat" or "groupchat.
    """
    try:
        iqresult = await self["xep_0030"].get_info(jid=jid)
        features = iqresult["disco_info"]["features"]
        # identity = iqresult['disco_info']['identities']
        # if 'account' in indentity:
        # if 'conference' in indentity:
        if 'http://jabber.org/protocol/muc' in features:
            return "groupchat"
        # TODO elif <feature var='jabber:iq:gateway'/>
        # NOTE Is it needed? We do not interact with gateways or services
        else:
            return "chat"
    # TODO Test whether this exception is realized
    except IqTimeout as e:
        messages = [
            ("Timeout IQ"),
            ("IQ Stanza:", e),
            ("Jabber ID:", jid)
            ]
        for message in messages:
            logging.error(message)