#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from slixfeed.xmpp.utility import get_chat_type


class XmppMessage:

    async def send(self, jid, message, chat_type=None):
        if not chat_type:
            chat_type = await get_chat_type(self, jid)
        self.send_message(
            mto=jid,
            mfrom=self.boundjid.bare,
            mbody=message,
            mtype=chat_type
            )


    async def send_oob(self, jid, url):
        chat_type = await get_chat_type(self, jid)
        html = (
            f'<body xmlns="http://www.w3.org/1999/xhtml">'
            f'<a href="{url}">{url}</a></body>')
        message = self.make_message(
            mto=jid,
            mfrom=self.boundjid.bare,
            mbody=url,
            mhtml=html,
            mtype=chat_type
            )
        message['oob']['url'] = url
        message.send()


    def send_reply(self, message, response):
        message.reply(response).send()