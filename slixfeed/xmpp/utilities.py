#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from slixfeed.log import Logger
from slixmpp.exceptions import IqError, IqTimeout

logger = Logger(__name__)

# class XmppChat
# class XmppUtility:

class XmppUtilities:

    def get_self_alias(self, room):
        """Get self alias of a given group chat"""
        jid_full = self.plugin['xep_0045'].get_our_jid_in_room(room)
        alias = jid_full.split('/')[1]
        return alias

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


    def is_access(self, jid, chat_type):
        """Determine access privilege"""
        room = jid_bare = jid.bare
        alias = jid.resource
        if chat_type == 'groupchat':
            access = True if XmppUtilities.is_moderator(self, room, alias) else False
            if access: print('Access granted to groupchat moderator ' + alias)
        else:
            print('Access granted to chat jid ' + jid_bare)
            access = True
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

    def is_admin(self, room, alias):
        """Check if given JID is an administrator"""
        affiliation = self.plugin['xep_0045'].get_jid_property(room, alias, 'affiliation')
        result = True if affiliation == 'admin' else False
        return result

    def is_owner(self, room, alias):
        """Check if given JID is an owner"""
        affiliation = self.plugin['xep_0045'].get_jid_property(room, alias, 'affiliation')
        result = True if affiliation == 'owner' else False
        return result

    def is_moderator(self, room, alias):
        """Check if given JID is a moderator"""
        role = self.plugin['xep_0045'].get_jid_property(room, alias, 'role')
        result = True if role == 'moderator' else False
        return result

    # NOTE Would this properly work when Alias and Local differ?
    def is_member(self, jid_bare, jid_full):
        """Check if given JID is a member"""
        alias = jid_full[jid_full.index('/')+1:]
        affiliation = self.plugin['xep_0045'].get_jid_property(jid_bare, alias, 'affiliation')
        result = True if affiliation == 'member' else False
        return result
