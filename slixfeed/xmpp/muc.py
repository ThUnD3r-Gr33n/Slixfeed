#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

TODO

1) Send message to inviter that bot has joined to groupchat.

2) If groupchat requires captcha, send the consequent message.

3) If groupchat error is received, send that error message to inviter.

"""

from slixmpp.plugins.xep_0048.stanza import Bookmarks

async def join_groupchat(self, inviter, muc_jid):
    # token = await initdb(
    #     muc_jid,
    #     get_settings_value,
    #     "token"
    #     )
    # if token != "accepted":
    #     token = randrange(10000, 99999)
    #     await initdb(
    #         muc_jid,
    #         set_settings_value,
    #         ["token", token]
    #     )
    #     self.send_message(
    #         mto=inviter,
    #         mbody=(
    #             "Send activation token {} to groupchat xmpp:{}?join."
    #             ).format(token, muc_jid)
    #         )
    print("muc_jid")
    print(muc_jid)
    self.plugin['xep_0045'].join_muc(
        muc_jid,
        self.nick,
        # If a room password is needed, use:
        # password=the_room_password,
        )
    await self.add_groupchat_to_bookmarks(muc_jid)
    messages = [
        "Greetings!",
        "I'm {}, the news anchor.".format(self.nick),
        "My job is to bring you the latest news "
        "from sources you provide me with.",
        "You may always reach me via "
        "xmpp:{}?message".format(self.boundjid.bare)
        ]
    for message in messages:
        self.send_message(
            mto=muc_jid,
            mbody=message,
            mtype="groupchat"
            )


async def add_groupchat_to_bookmarks(self, muc_jid):
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


async def close_groupchat(self, muc_jid):
    messages = [
        "Whenever you need an RSS service again, "
        "please don’t hesitate to contact me.",
        "My personal contact is xmpp:{}?message".format(self.boundjid.bare),
        "Farewell, and take care."
        ]
    for message in messages:
        self.send_message(
            mto=muc_jid,
            mbody=message,
            mtype="groupchat"
            )
    await self.remove_groupchat_from_bookmarks(muc_jid)
    self.plugin['xep_0045'].leave_muc(
        muc_jid,
        self.nick,
        "Goodbye!",
        self.boundjid.bare
        )


async def remove_groupchat_from_bookmarks(self, muc_jid):
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
