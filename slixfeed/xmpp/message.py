#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
# import slixfeed.action as action
import slixfeed.config as config
from slixfeed.dt import current_time, timestamp
import slixfeed.fetch as fetch
import slixfeed.sqlite as sqlite
import slixfeed.task as task
import slixfeed.url as uri
from slixfeed.xmpp.bookmark import XmppBookmark
# from slixfeed.xmpp.muc import XmppGroupchat
# from slixfeed.xmpp.message import XmppMessage
from slixfeed.xmpp.presence import XmppPresence
from slixfeed.xmpp.upload import XmppUpload
from slixfeed.xmpp.utility import get_chat_type
import time

"""

NOTE

See XEP-0367: Message Attaching

"""

class XmppMessage:


    # def process():


    def send(self, jid, message_body, chat_type):
        self.send_message(mto=jid,
                          mfrom=self.boundjid.bare,
                          mbody=message_body,
                          mtype=chat_type)


    def send_headline(self, jid, message_subject, message_body, chat_type):
        self.send_message(mto=jid,
                          mfrom=self.boundjid.bare,
                          # mtype='headline',
                          msubject=message_subject,
                          mbody=message_body,
                          mtype=chat_type,
                          mnick=self.alias)


    def send_oob(self, jid, url, chat_type):
        html = (
            f'<body xmlns="http://www.w3.org/1999/xhtml">'
            f'<a href="{url}">{url}</a></body>')
        message = self.make_message(mto=jid,
                                    mfrom=self.boundjid.bare,
                                    mbody=url,
                                    mhtml=html,
                                    mtype=chat_type)
        message['oob']['url'] = url
        message.send()


    # FIXME Solve this function
    def send_oob_reply_message(message, url, response):
        reply = message.reply(response)
        reply['oob']['url'] = url
        reply.send()


    # def send_reply(self, message, message_body):
    #     message.reply(message_body).send()


    def send_reply(self, message, response):
        message.reply(response).send()
