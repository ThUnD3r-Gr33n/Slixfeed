#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

TODO

1) Function to list bookmarks

"""


from slixmpp.plugins.xep_0048.stanza import Bookmarks


async def add(self, muc_jid):
    result = await self.plugin['xep_0048'].get_bookmarks()
    bookmarks = result["private"]["bookmarks"]
    conferences = bookmarks["conferences"]
    mucs = []
    for conference in conferences:
        jid = conference["jid"]
        mucs.extend([jid])
    if muc_jid not in mucs:
        bookmarks = Bookmarks()
        mucs.extend([muc_jid])
        for muc in mucs:
            bookmarks.add_conference(
                muc,
                self.nick,
                autojoin=True
                )
        await self.plugin['xep_0048'].set_bookmarks(bookmarks)
    # bookmarks = Bookmarks()
    # await self.plugin['xep_0048'].set_bookmarks(bookmarks)
    # print(await self.plugin['xep_0048'].get_bookmarks())

    # bm = BookmarkStorage()
    # bm.conferences.append(Conference(muc_jid, autojoin=True, nick=self.nick))
    # await self['xep_0402'].publish(bm)


async def remove(self, muc_jid):
    result = await self.plugin['xep_0048'].get_bookmarks()
    bookmarks = result["private"]["bookmarks"]
    conferences = bookmarks["conferences"]
    mucs = []
    for conference in conferences:
        jid = conference["jid"]
        mucs.extend([jid])
    if muc_jid in mucs:
        bookmarks = Bookmarks()
        mucs.remove(muc_jid)
        for muc in mucs:
            bookmarks.add_conference(
                muc,
                self.nick,
                autojoin=True
                )
        await self.plugin['xep_0048'].set_bookmarks(bookmarks)
