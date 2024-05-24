#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

TODO

1) Send message to inviter that bot has joined to groupchat.

2) If groupchat requires captcha, send the consequent message.

3) If groupchat error is received, send that error message to inviter.

FIXME

1) Save name of groupchat instead of jid as name

"""
import logging
from slixmpp.exceptions import IqError, IqTimeout, PresenceError

class XmppGroupchat:

    async def join(self, jid, alias=None, password=None):
        # token = await initdb(
        #     muc_jid,
        #     sqlite.get_setting_value,
        #     "token"
        #     )
        # if token != "accepted":
        #     token = randrange(10000, 99999)
        #     await initdb(
        #         muc_jid,
        #         sqlite.update_setting_value,
        #         ["token", token]
        #     )
        #     self.send_message(
        #         mto=inviter,
        #         mfrom=self.boundjid.bare,
        #         mbody=(
        #             "Send activation token {} to groupchat xmpp:{}?join."
        #             ).format(token, muc_jid)
        #         )
        logging.info('Joining groupchat\n'
                     'JID     : {}\n'
                     .format(jid))
        jid_from = str(self.boundjid) if self.is_component else None
        if alias == None: self.alias
        try:
            await self.plugin['xep_0045'].join_muc_wait(jid,
                                                        alias,
                                                        presence_options = {"pfrom" : jid_from},
                                                        password=password,
                                                        maxchars=0,
                                                        maxstanzas=0,
                                                        seconds=0,
                                                        since=0,
                                                        timeout=30)
            result = 'joined ' + jid
        except IqError as e:
            logging.error('Error XmppIQ')
            logging.error(str(e))
            logging.error(jid)
            result = 'error'
        except IqTimeout as e:
            logging.error('Timeout XmppIQ')
            logging.error(str(e))
            logging.error(jid)
            result = 'timeout'
        except PresenceError as e:
            logging.error('Error Presence')
            logging.error(str(e))
            if (e.condition == 'forbidden' and
                e.presence['error']['code'] == '403'):
                logging.warning('{} is banned from {}'.format(self.alias, jid))
                result = 'ban'
            else:
                result = 'error'
        return result


    def leave(self, jid):
        jid_from = str(self.boundjid) if self.is_component else None
        message = ('This news bot will now leave this groupchat.\n'
                   'The JID of this news bot is xmpp:{}?message'
                   .format(self.boundjid.bare))
        status_message = ('This bot has left the group. '
                         'It can be reached directly via {}'
                         .format(self.boundjid.bare))
        self.send_message(mto=jid,
                          mfrom=self.boundjid,
                          mbody=message,
                          mtype='groupchat')
        self.plugin['xep_0045'].leave_muc(jid,
                                          self.alias,
                                          status_message,
                                          jid_from)
