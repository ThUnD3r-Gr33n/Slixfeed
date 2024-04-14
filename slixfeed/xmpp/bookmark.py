#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

TODO

1) Save groupchat name instead of jid in field name.

"""

from slixmpp.plugins.xep_0048.stanza import Bookmarks


class XmppBookmark:


    async def get_bookmarks(self):
        result = await self.plugin['xep_0048'].get_bookmarks()
        conferences = result['private']['bookmarks']['conferences']
        return conferences


    async def get_bookmark_properties(self, jid):
        result = await self.plugin['xep_0048'].get_bookmarks()
        groupchats = result['private']['bookmarks']['conferences']
        for groupchat in groupchats:
            if jid == groupchat['jid']:
                properties = {'password': groupchat['password'],
                              'jid': groupchat['jid'],
                              'name': groupchat['name'],
                              'nick': groupchat['nick'],
                              'autojoin': groupchat['autojoin'],
                              'lang': groupchat['lang']}
                break
        return properties


    async def add(self, jid=None, properties=None):
        result = await self.plugin['xep_0048'].get_bookmarks()
        conferences = result['private']['bookmarks']['conferences']
        groupchats = []
        if properties:
            properties['jid'] = properties['room'] + '@' + properties['host']
            if not properties['alias']: properties['alias'] = self.alias
        else:
            properties = {
                'jid' : jid,
                'alias' : self.alias,
                'name' : jid.split('@')[0],
                'autojoin' : True,
                'password' : None,
                }
        for conference in conferences:
            if conference['jid'] != properties['jid']:
                groupchats.extend([conference])
        # FIXME Ad-hoc bookmark form is stuck
        # if jid not in groupchats:
        if properties['jid'] not in groupchats:
            bookmarks = Bookmarks()
            for groupchat in groupchats:
                # if groupchat['jid'] == groupchat['name']:
                #     groupchat['name'] = groupchat['name'].split('@')[0]
                bookmarks.add_conference(groupchat['jid'],
                                         groupchat['nick'],
                                         name=groupchat['name'],
                                         autojoin=groupchat['autojoin'],
                                         password=groupchat['password'])
            bookmarks.add_conference(properties['jid'],
                                     properties['alias'],
                                     name=properties['name'],
                                     autojoin=properties['autojoin'],
                                     password=properties['password'])
            # await self.plugin['xep_0048'].set_bookmarks(bookmarks)
            self.plugin['xep_0048'].set_bookmarks(bookmarks)
        # bookmarks = Bookmarks()
        # await self.plugin['xep_0048'].set_bookmarks(bookmarks)
        # print(await self.plugin['xep_0048'].get_bookmarks())

        # bm = BookmarkStorage()
        # bm.conferences.append(Conference(muc_jid, autojoin=True, nick=self.alias))
        # await self['xep_0402'].publish(bm)


    async def remove(self, jid):
        result = await self.plugin['xep_0048'].get_bookmarks()
        conferences = result['private']['bookmarks']['conferences']
        groupchats = []
        for conference in conferences:
            if not conference['jid'] == jid:
                groupchats.extend([conference])
        bookmarks = Bookmarks()
        for groupchat in groupchats:
            bookmarks.add_conference(groupchat['jid'],
                                     groupchat['nick'],
                                     name=groupchat['name'],
                                     autojoin=groupchat['autojoin'],
                                     password=groupchat['password'])
        await self.plugin['xep_0048'].set_bookmarks(bookmarks)
