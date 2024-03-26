#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Functions create_node and create_entry are derived from project atomtopubsub.

"""

import hashlib
import slixmpp.plugins.xep_0060.stanza.pubsub as pubsub
from slixmpp.xmlstream import ET

class XmppPubsub:


    async def get_pubsub_services(self):
        jids = [self.boundjid.bare]
        iq = await self['xep_0030'].get_items(jid=self.boundjid.domain)
        items = iq['disco_items']['items']
        for item in items:
            iq = await self['xep_0030'].get_info(jid=item[0])
            identities = iq['disco_info']['identities']
            for identity in identities:
                if identity[0] == 'pubsub' and identity[1] == 'service':
                    jid = item[0]
                    jids.extend([jid])
        return jids


    # TODO Make use of var "xep" with match/case (XEP-0060, XEP-0277, XEP-0472)
    def create_node(self, jid, node, xep ,title, summary=None):
        jid_from = str(self.boundjid) if self.is_component else None
        iq = self.Iq(stype='set',
                     sto=jid,
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


    def create_entry(self, jid, node, entry, version):
        iq = self.Iq(stype="set", sto=jid)
        iq['pubsub']['publish']['node'] = node

        item = pubsub.Item()

        # From atomtopubsub:
        # character / is causing a bug in movim. replacing : and , with - in id.
        # It provides nicer urls.
        
        # Respond to atomtopubsub:
        # I think it would be beneficial to use md5 checksum of Url as Id for
        # cross reference, and namely - in another project to utilize PubSub as
        # links sharing system (see del.icio.us) - to share node entries.

        # NOTE Warning: Entry might not have a link
        # TODO Handle situation error
        url_encoded = entry.link.encode()
        url_hashed = hashlib.md5(url_encoded)
        url_digest = url_hashed.hexdigest()
        item['id'] = url_digest

        node_entry = ET.Element("entry")
        node_entry.set('xmlns', 'http://www.w3.org/2005/Atom')

        title = ET.SubElement(node_entry, "title")
        title.text = entry['title']

        updated = ET.SubElement(node_entry, "updated")
        updated.text = entry['updated']

        # Content
        if version == 'atom3':

            if hasattr(entry.content[0], 'type'):
                content = ET.SubElement(node_entry, "content")
                content.set('type', entry.content[0].type)
                content.text = entry.content[0].value

        elif version =='rss20' or 'rss10' or 'atom10':
            if hasattr(entry, "content"):
                content = ET.SubElement(node_entry, "content")
                content.set('type', 'text/html')
                content.text = entry.content[0].value

            elif hasattr(entry, "description"):
                content = ET.SubElement(node_entry,"content")
                content.set('type', 'text/html')
                content.text = entry.description
                print('In Description - PublishX')

        # Links
        if hasattr(entry, 'links'):
            for l in entry.links:
                link = ET.SubElement(node_entry, "link")
                if hasattr(l, 'href'):
                    link.set('href', l['href'])
                    link.set('type', l['type'])
                    link.set('rel', l['rel'])
                elif hasattr(entry, 'link'):
                    link.set('href', entry['link'])

        # Tags
        if hasattr(entry, 'tags'):
            for t in entry.tags:
                tag = ET.SubElement(node_entry, "category")
                tag.set('term', t.term)

        # Categories
        if hasattr(entry,'category'):
            for c in entry["category"]:
                cat = ET.SubElement(node_entry, "category")
                cat.set('category', entry.category[0])

        # Authors
        if version == 'atom03':
            if hasattr(entry, 'authors'):
                author = ET.SubElement(node_entry, "author")
                name = ET.SubElement(author, "name")
                name.text = entry.authors[0].name
                if hasattr(entry.authors[0], 'href'):
                    uri = ET.SubElement(author, "uri")
                    uri.text = entry.authors[0].href
        
        elif version == 'rss20' or 'rss10' or 'atom10':
            if hasattr(entry, 'author'):
                author = ET.SubElement(node_entry, "author")
                name = ET.SubElement(node_entry, "author")
                name.text = entry.author
            
                if hasattr(entry.author, 'href'):
                    uri = ET.SubElement(author, "uri")
                    uri.text = entry.authors[0].href
                    
        item['payload'] = node_entry

        iq['pubsub']['publish'].append(item)

        return iq
