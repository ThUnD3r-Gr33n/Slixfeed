#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from slixmpp.exceptions import IqTimeout
import logging


async def get_chat_type(self, jid):
    """
    Check whether a JID is of MUC.

    If iqresult["disco_info"]["features"] contains XML namespace
    of 'http://jabber.org/protocol/muc', then it is a "groupchat".

    Unless it has forward slash, which would indicate that it is
    a chat which is conducted through a groupchat.
    
    Otherwise, determine type "chat".

    Parameters
    ----------
    jid : str
        Jabber ID.

    Returns
    -------
    chat_type : str
        "chat" or "groupchat.
    """
    try:
        iqresult = await self["xep_0030"].get_info(jid=jid)
        features = iqresult["disco_info"]["features"]
        # identity = iqresult['disco_info']['identities']
        # if 'account' in indentity:
        # if 'conference' in indentity:
        if ('http://jabber.org/protocol/muc' in features) and not ('/' in jid):
            chat_type = "groupchat"
        # TODO elif <feature var='jabber:iq:gateway'/>
        # NOTE Is it needed? We do not interact with gateways or services
        else:
            chat_type = "chat"
        print('JID {} chat type is {}'.format(jid, chat_type))
        return chat_type
    # TODO Test whether this exception is realized
    except IqTimeout as e:
        messages = [
            ("Timeout IQ"),
            ("IQ Stanza:", e),
            ("Jabber ID:", jid)
            ]
        for message in messages:
            logging.error(message)