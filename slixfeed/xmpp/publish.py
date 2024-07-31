#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Functions create_node and create_entry are derived from project atomtopubsub.

"""

import asyncio
import hashlib
import slixmpp.plugins.xep_0060.stanza.pubsub as pubsub
from slixmpp.xmlstream import ET
import slixfeed.config as config
from slixfeed.config import Config
from slixfeed.log import Logger
import slixfeed.sqlite as sqlite
from slixfeed.syndication import Feed
from slixfeed.utilities import String, Url, Utilities
from slixfeed.xmpp.iq import XmppIQ
import sys
import time

logger = Logger(__name__)


class XmppPubsub:


    async def get_pubsub_services(self):
        results = []
        iq = await self['xep_0030'].get_items(jid=self.boundjid.domain)
        items = iq['disco_items']['items']
        for item in items:
            iq = await self['xep_0030'].get_info(jid=item[0])
            identities = iq['disco_info']['identities']
            for identity in identities:
                if identity[0] == 'pubsub' and identity[1] == 'service':
                    result = {}
                    result['jid'] = item[0]
                    if item[1]: result['name'] =  item[1]
                    elif item[2]: result['name'] = item[2]
                    else: result['name'] = item[0]
                    results.extend([result])
        return results


    async def get_node_properties(self, jid, node):
        config = await self.plugin['xep_0060'].get_node_config(jid, node)
        subscriptions = await self.plugin['xep_0060'].get_node_subscriptions(jid, node)
        affiliations = await self.plugin['xep_0060'].get_node_affiliations(jid, node)
        properties = {'config': config,
                      'subscriptions': subscriptions,
                      'affiliations': affiliations}
        breakpoint()
        return properties


    async def get_node_configuration(self, jid, node_id):
        node = await self.plugin['xep_0060'].get_node_config(jid, node_id)
        if not node:
            print('NODE CONFIG', node_id, str(node))
        return node


    async def get_nodes(self, jid):
        nodes = await self.plugin['xep_0060'].get_nodes(jid)
        # 'self' would lead to slixmpp.jid.InvalidJID: idna validation failed:
        return nodes


    async def get_item(self, jid, node, item_id):
        item = await self.plugin['xep_0060'].get_item(jid, node, item_id)
        return item


    async def get_items(self, jid, node):
        items = await self.plugin['xep_0060'].get_items(jid, node)
        return items


    def delete_node(self, jid, node):
        jid_from = str(self.boundjid) if self.is_component else None
        self.plugin['xep_0060'].delete_node(jid, node, ifrom=jid_from)


    def purge_node(self, jid, node):
        jid_from = str(self.boundjid) if self.is_component else None
        self.plugin['xep_0060'].purge(jid, node, ifrom=jid_from)
        # iq = self.Iq(stype='set',
        #              sto=jid,
        #              sfrom=jid_from)
        # iq['pubsub']['purge']['node'] = node
        # return iq


    # TODO Make use of var "xep" with match/case (XEP-0060, XEP-0277, XEP-0472)
    def create_node(self, jid, node, xep ,title=None, subtitle=None):
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
                      value=subtitle)
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
        form.addField('pubsub#type',
                      ftype='text-single',
                      value='http://www.w3.org/2005/Atom')
        return iq


    # TODO Consider to create a separate function called "create_atom_entry"
    # or "create_rfc4287_entry" for anything related to variable "node_entry".
    def create_entry(self, jid, node_id, item_id, node_item):
        iq = self.Iq(stype="set", sto=jid)
        iq['pubsub']['publish']['node'] = node_id

        item = pubsub.Item()

        # From atomtopubsub:
        # character / is causing a bug in movim. replacing : and , with - in id.
        # It provides nicer urls.
        
        # Respond to atomtopubsub:
        # I think it would be beneficial to use md5 checksum of Url as Id for
        # cross reference, and namely - in another project to utilize PubSub as
        # links sharing system (see del.icio.us) - to share node entries.

        item['id'] = item_id
        item['payload'] = node_item
        iq['pubsub']['publish'].append(item)

        return iq


    def _create_entry(self, jid, node, entry, version):
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
        item['id'] = url_digest + '_html'

        node_entry = ET.Element("entry")
        node_entry.set('xmlns', 'http://www.w3.org/2005/Atom')

        title = ET.SubElement(node_entry, "title")
        title.text = entry.title

        updated = ET.SubElement(node_entry, "updated")
        updated.text = entry.updated

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


class XmppPubsubAction:


    async def send_selected_entry(self, jid_bare, node_id, entry_id):
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_bare: {}'.format(function_name, jid_bare))
        db_file = config.get_pathname_to_database(jid_bare)
        report = {}
        if jid_bare == self.boundjid.bare:
            node_id = 'urn:xmpp:microblog:0'
            node_subtitle = None
            node_title = None
        else:
            feed_id = sqlite.get_feed_id_by_entry_index(db_file, entry_id)
            feed_id = feed_id[0]
            node_id, node_title, node_subtitle = sqlite.get_feed_properties(db_file, feed_id)
            print('THIS IS A TEST')
            print(node_id)
            print(node_title)
            print(node_subtitle)
            print('THIS IS A TEST')
        xep = None
        iq_create_node = XmppPubsub.create_node(
            self, jid_bare, node_id, xep, node_title, node_subtitle)
        await XmppIQ.send(self, iq_create_node)
        entry = sqlite.get_entry_properties(db_file, entry_id)
        print('xmpp_pubsub_send_selected_entry',jid_bare)
        print(node_id)
        entry_dict = Feed.pack_entry_into_dict(db_file, entry)
        node_item = Feed.create_rfc4287_entry(entry_dict)
        entry_url = entry_dict['link']
        item_id = Utilities.hash_url_to_md5(entry_url)
        iq_create_entry = XmppPubsub.create_entry(
            self, jid_bare, node_id, item_id, node_item)
        await XmppIQ.send(self, iq_create_entry)
        await sqlite.mark_as_read(db_file, entry_id)
        report = entry_url
        return report
    
    
    async def send_unread_items(self, jid_bare):
        """
    
        Parameters
        ----------
        jid_bare : TYPE
            Bare Jabber ID.
    
        Returns
        -------
        report : dict
            URL and Number of processed entries.
    
        """
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_bare: {}'.format(function_name, jid_bare))
        db_file = config.get_pathname_to_database(jid_bare)
        report = {}
        subscriptions = sqlite.get_active_feeds_url(db_file)
        for url in subscriptions:
            url = url[0]
            # feed_id = sqlite.get_feed_id(db_file, url)
            # feed_id = feed_id[0]
            # feed_properties = sqlite.get_feed_properties(db_file, feed_id)
            feed_id = sqlite.get_feed_id(db_file, url)
            feed_id = feed_id[0]
    
            # Publish to node 'urn:xmpp:microblog:0' for own JID
            # Publish to node based on feed identifier for PubSub service.
    
            if jid_bare == self.boundjid.bare:
                node_id = 'urn:xmpp:microblog:0'
                node_subtitle = None
                node_title = None
            else:
                # node_id = feed_properties[2]
                # node_title = feed_properties[3]
                # node_subtitle = feed_properties[5]
                node_id = sqlite.get_feed_identifier(db_file, feed_id)
                node_id = node_id[0]
                if not node_id:
                    counter = 0
                    while True:
                        identifier = String.generate_identifier(url, counter)
                        if sqlite.check_identifier_exist(db_file, identifier):
                            counter += 1
                        else:
                            break
                    await sqlite.update_feed_identifier(db_file, feed_id, identifier)
                    node_id = sqlite.get_feed_identifier(db_file, feed_id)
                    node_id = node_id[0]
                node_title = sqlite.get_feed_title(db_file, feed_id)
                node_title = node_title[0]
                node_subtitle = sqlite.get_feed_subtitle(db_file, feed_id)
                node_subtitle = node_subtitle[0]
            xep = None
            node_exist = await XmppPubsub.get_node_configuration(self, jid_bare, node_id)
            if not node_exist:
                iq_create_node = XmppPubsub.create_node(
                    self, jid_bare, node_id, xep, node_title, node_subtitle)
                await XmppIQ.send(self, iq_create_node)
            entries = sqlite.get_unread_entries_of_feed(db_file, feed_id)
            report[url] = len(entries)
            for entry in entries:
                feed_entry = Feed.pack_entry_into_dict(db_file, entry)
                node_entry = Feed.create_rfc4287_entry(feed_entry)
                entry_url = feed_entry['link']
                item_id = Utilities.hash_url_to_md5(entry_url)
                print('PubSub node item was sent to', jid_bare, node_id)
                print(entry_url)
                print(item_id)
                iq_create_entry = XmppPubsub.create_entry(
                    self, jid_bare, node_id, item_id, node_entry)
                await XmppIQ.send(self, iq_create_entry)
                ix = entry[0]
                await sqlite.mark_as_read(db_file, ix)
        print(report)
        return report


class XmppPubsubTask:


    def loop_task(self, jid_bare):
        db_file = config.get_pathname_to_database(jid_bare)
        if jid_bare not in self.settings:
            Config.add_settings_jid(self, jid_bare, db_file)
        while True:
            if jid_bare not in self.task_manager:
                self.task_manager[jid_bare] = {}
                logger.info('Creating new task manager for JID {}'.format(jid_bare))
            logger.info('Stopping task "publish" for JID {}'.format(jid_bare))
            try:
                self.task_manager[jid_bare]['publish'].cancel()
            except:
                logger.info('No task "publish" for JID {} (XmppPubsubAction.send_unread_items)'
                            .format(jid_bare))
            logger.info('Starting tasks "publish" for JID {}'.format(jid_bare))
            self.task_manager[jid_bare]['publish'] = asyncio.create_task(
                XmppPubsubAction.send_unread_items(self, jid_bare))
            time.sleep(60 * 180)


    def restart_task(self, jid_bare):
        db_file = config.get_pathname_to_database(jid_bare)
        if jid_bare not in self.settings:
            Config.add_settings_jid(self, jid_bare, db_file)
        if jid_bare not in self.task_manager:
            self.task_manager[jid_bare] = {}
            logger.info('Creating new task manager for JID {}'.format(jid_bare))
        logger.info('Stopping task "publish" for JID {}'.format(jid_bare))
        try:
            self.task_manager[jid_bare]['publish'].cancel()
        except:
            logger.info('No task "publish" for JID {} (XmppPubsubAction.send_unread_items)'
                        .format(jid_bare))
        logger.info('Starting tasks "publish" for JID {}'.format(jid_bare))
        self.task_manager[jid_bare]['publish'] = asyncio.create_task(
            XmppPubsubAction.send_unread_items(self, jid_bare))


    async def task_publish(self, jid_bare):
        db_file = config.get_pathname_to_database(jid_bare)
        if jid_bare not in self.settings:
            Config.add_settings_jid(self, jid_bare, db_file)
        while True:
            await XmppPubsubAction.send_unread_items(self, jid_bare)
            await asyncio.sleep(60 * 180)
