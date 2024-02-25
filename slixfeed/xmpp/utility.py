#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from slixmpp.exceptions import IqError, IqTimeout
import logging

# class XmppChat
# class XmppUtility:

def is_moderator(self, jid, jid_full):
    alias = jid_full[jid_full.index('/')+1:]
    role = self.plugin['xep_0045'].get_jid_property(jid, alias, 'role')
    if role == 'moderator':
        return True
    else:
        return False


# TODO Rename to get_jid_type
async def get_chat_type(self, jid):
    """
    Check chat (i.e. JID) type.

    If iqresult["disco_info"]["features"] contains XML namespace
    of 'http://jabber.org/protocol/muc', then it is a 'groupchat'.

    Unless it has forward slash, which would indicate that it is
    a chat which is conducted through a groupchat.
    
    Otherwise, determine type 'chat'.

    Parameters
    ----------
    jid : str
        Jabber ID.

    Returns
    -------
    chat_type : str
        'chat' or 'groupchat'.
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
        logging.info('Jabber ID: {}\n'
                     'Chat Type: {}'.format(jid, chat_type))
        return chat_type
    # TODO Test whether this exception is realized
    except IqError as e:
        message = ('IQ Error\n'
                   'IQ Stanza: {}'
                   'Jabber ID: {}'
                   .format(e, jid))
        logging.error(message)
    except IqTimeout as e:
        message = ('IQ Timeout\n'
                   'IQ Stanza: {}'
                   'Jabber ID: {}'
                   .format(e, jid))
        logging.error(message)
    # except BaseException as e:
    #     logging.error('BaseException', str(e))
    # finally:
    #     logging.info('Chat type is:', chat_type)
