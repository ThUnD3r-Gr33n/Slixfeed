#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from slixfeed.log import Logger
from slixmpp.exceptions import IqError, IqTimeout

logger = Logger(__name__)

# class XmppChat
# class XmppUtility:

    
class XmppUtilities:

    
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
        result : str
            'chat' or 'groupchat' or 'error'.
        """
        try:
            iqresult = await self["xep_0030"].get_info(jid=jid)
            features = iqresult["disco_info"]["features"]
            # identity = iqresult['disco_info']['identities']
            # if 'account' in indentity:
            # if 'conference' in indentity:
            if ('http://jabber.org/protocol/muc' in features) and not ('/' in jid):
                result = "groupchat"
            # TODO elif <feature var='jabber:iq:gateway'/>
            # NOTE Is it needed? We do not interact with gateways or services
            else:
                result = "chat"
            logger.info('Jabber ID: {}\n'
                         'Chat Type: {}'.format(jid, result))
        except (IqError, IqTimeout) as e:
            logger.warning('Chat type could not be determined for {}'.format(jid))
            logger.error(e)
            result = 'error'
        # except BaseException as e:
        #     logger.error('BaseException', str(e))
        # finally:
        #     logger.info('Chat type is:', chat_type)
        return result



    def is_access(self, jid_bare, jid_full, chat_type):
        """Determine access privilege"""
        operator = XmppUtilities.is_operator(self, jid_bare)
        if operator:
            if chat_type == 'groupchat':
                if XmppUtilities.is_moderator(self, jid_bare, jid_full):
                    access = True
            else:
                access = True
        else:
            access = False
        return access
    
    
    def is_operator(self, jid_bare):
        """Check if given JID is an operator"""
        result = False
        for operator in self.operators:
            if jid_bare == operator['jid']:
                result = True
                # operator_name = operator['name']
                break
        return result
    
    
    def is_moderator(self, jid_bare, jid_full):
        """Check if given JID is a moderator"""
        alias = jid_full[jid_full.index('/')+1:]
        role = self.plugin['xep_0045'].get_jid_property(jid_bare, alias, 'role')
        if role == 'moderator':
            result = True
        else:
            result = False
        return result
    
    
    def is_member(self, jid_bare, jid_full):
        """Check if given JID is a member"""
        alias = jid_full[jid_full.index('/')+1:]
        affiliation = self.plugin['xep_0045'].get_jid_property(jid_bare, alias, 'affiliation')
        if affiliation == 'member':
            result = True
        else:
            result = False
        return result