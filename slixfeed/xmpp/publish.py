#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# TODO Implement XEP-0472: Pubsub Social Feed

class XmppPubsub:

    def create(self, title, summary, node, server):
        jid_from = str(self.boundjid) if self.is_component else None
        iq = self.Iq(stype="set",
                     sto=server,
                     sfrom=jid_from)
        iq['pubsub']['create']['node'] = node
        form = iq['pubsub']['configure']['form']
        form['type'] = 'submit'
        form.addField('pubsub#title',
                      ftype='text-single',
                      value=title)
        form.addField('pubsub#description',
                      ftype='text-single',
                      value=summary)
        form.addField('pubsub#notify_retract',
                      ftype='boolean',
                      value=1)
        form.addField('pubsub#max_items',
                      ftype='text-single',
                      value='20')
        form.addField('pubsub#persist_items',
                      ftype='boolean',
                      value=1)
        form.addField('pubsub#send_last_published_item',
                      ftype='text-single',
                      value='never')
        form.addField('pubsub#deliver_payloads',
                      ftype='boolean',
                      value=0)

        # TODO

        form.addField('pubsub#type',
                      ftype='text-single',
                      value='http://www.w3.org/2005/Atom')

        return iq
