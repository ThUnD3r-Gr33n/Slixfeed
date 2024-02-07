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

FIXME

ERROR:asyncio:Task exception was never retrieved
future: <Task finished name='Task-3410' coro=<send_update() done, defined at /home/admin/.venv/lib/python3.11/site-packages/slixfeed/task.py:181> exception=ParseError('not well-formed (invalid token): line 1, column 198')>
Traceback (most recent call last):
  File "/home/jojo/.venv/lib/python3.11/site-packages/slixfeed/task.py", line 237, in send_update
    XmppMessage.send_oob(self, jid, media, chat_type)
  File "/home/jojo/.venv/lib/python3.11/site-packages/slixfeed/xmpp/message.py", line 56, in send_oob
    message = self.make_message(mto=jid,
              ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/jojo/.venv/lib/python3.11/site-packages/slixmpp/basexmpp.py", line 517, in make_message
    message['html']['body'] = mhtml
    ~~~~~~~~~~~~~~~^^^^^^^^
  File "/home/jojo/.venv/lib/python3.11/site-packages/slixmpp/xmlstream/stanzabase.py", line 792, in __setitem__
    getattr(self, set_method)(value, **kwargs)
  File "/home/jojo/.venv/lib/python3.11/site-packages/slixmpp/plugins/xep_0071/stanza.py", line 38, in set_body
    xhtml = ET.fromstring(content)
            ^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.11/xml/etree/ElementTree.py", line 1338, in XML
    parser.feed(text)
xml.etree.ElementTree.ParseError: not well-formed (invalid token): line 1, column 198

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
        try:
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
        except:
            logging.error('ERROR!')
            logging.error(jid, url, chat_type, html)


    # FIXME Solve this function
    def send_oob_reply_message(message, url, response):
        reply = message.reply(response)
        reply['oob']['url'] = url
        reply.send()


    # def send_reply(self, message, message_body):
    #     message.reply(message_body).send()


    def send_reply(self, message, response):
        message.reply(response).send()
