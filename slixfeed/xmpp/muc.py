#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

TODO

1) Send message to inviter that bot has joined to groupchat.

2) If groupchat requires captcha, send the consequent message.

3) If groupchat error is received, send that error message to inviter.

"""
import logging
import slixfeed.xmpp.bookmark as bookmark
import slixfeed.xmpp.process as process
from slixfeed.datetime import current_time

# async def accept_muc_invite(self, message, ctr=None):
#     # if isinstance(message, str):
#     if not ctr:
#         ctr = message["from"].bare
#         jid = message['groupchat_invite']['jid']
#     else:
#         jid = message
async def accept_invitation(self, message):
    # operator muc_chat
    inviter = message["from"].bare
    muc_jid = message['groupchat_invite']['jid']
    await join(self, inviter, muc_jid)


async def autojoin(self, event):
    result = await self.plugin['xep_0048'].get_bookmarks()
    bookmarks = result["private"]["bookmarks"]
    conferences = bookmarks["conferences"]
    for conference in conferences:
        if conference["autojoin"]:
            muc_jid = conference["jid"]
            logging.debug("Autojoin groupchat", muc_jid)
            self.plugin['xep_0045'].join_muc(
                muc_jid,
                self.nick,
                # If a room password is needed, use:
                # password=the_room_password,
                )

async def join(self, inviter, muc_jid):
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
    await bookmark.add(self, muc_jid)
    process.greet(self, muc_jid, chat_type="groupchat")


async def leave(self, muc_jid):
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
    await bookmark.remove(self, muc_jid)
    self.plugin['xep_0045'].leave_muc(
        muc_jid,
        self.nick,
        "Goodbye!",
        self.boundjid.bare
        )

