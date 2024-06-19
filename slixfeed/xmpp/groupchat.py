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
from slixfeed.xmpp.bookmark import XmppBookmark
from slixfeed.xmpp.muc import XmppMuc
from slixfeed.log import Logger, Message

logger = Logger(__name__)


class XmppGroupchat:

    async def autojoin(self, bookmarks):
        for bookmark in bookmarks:
            if bookmark["jid"] and bookmark["autojoin"]:
                if not bookmark["nick"]:
                    bookmark["nick"] = self.alias
                    logger.error('Alias (i.e. Nicknname) is missing for '
                                  'bookmark {}'.format(bookmark['name']))
                alias = bookmark["nick"]
                muc_jid = bookmark["jid"]
                Message.printer('Joining to MUC {} ...'.format(muc_jid))
                result = await XmppMuc.join(self, muc_jid, alias)
                if result == 'ban':
                    await XmppBookmark.remove(self, muc_jid)
                    logger.warning('{} is banned from {}'.format(self.alias, muc_jid))
                    logger.warning('Groupchat {} has been removed from bookmarks'
                                   .format(muc_jid))
                else:
                    logger.info('Autojoin groupchat\n'
                                'Name  : {}\n'
                                'JID   : {}\n'
                                'Alias : {}\n'
                                .format(bookmark["name"],
                                        bookmark["jid"],
                                        bookmark["nick"]))
            elif not bookmark["jid"]:
                logger.error('JID is missing for bookmark {}'
                              .format(bookmark['name']))
        print('Done')
