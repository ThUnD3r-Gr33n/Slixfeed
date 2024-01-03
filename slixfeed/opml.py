#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

{
 'bozo': False, 
 'bozo_exception': None, 
 'feeds': [
     {
      'url': 'https://kurtmckee.org/tag/listparser/feed', 
      'title': 'listparser blog', 
      'categories': [], 
      'tags': []
      }, 
     {
      'url': 'https://github.com/kurtmckee/listparser/commits/develop.atom', 
      'title': 'listparser changelog', 
      'categories': [], 
      'tags': []
      }
     ], 
 'lists': [], 
 'opportunities': [], 
 'meta': {
     'title': 'listparser project feeds', 
     'author': {
         'name': 'Kurt McKee', 
         'email': 'contactme@kurtmckee.org', 
         'url': 'https://kurtmckee.org/'
         }
     }, 
 'version': 'opml2'
 }

import listparser
import lxml


async def import_from_file(db_file, opml_doc):
    feeds = listparser.parse(opml_doc)['feeds']
    for feed in feeds:
        url = feed['url']
        title = feed['title']
        # categories = feed['categories']
        # tags = feed['tags']
        # await datahandler.add_feed_no_check(db_file, [url, title])

"""

from slixfeed.datetime import current_time
import xml.etree.ElementTree as ET

# NOTE Use OPyML or LXML
def export_to_file(jid, filename, results):
    root = ET.Element("opml")
    root.set("version", "1.0")
    head = ET.SubElement(root, "head")
    ET.SubElement(head, "title").text = "Subscriptions for {}".format(jid)
    ET.SubElement(head, "description").text = (
        "Set of feeds exported with Slixfeed")
    ET.SubElement(head, "generator").text = "Slixfeed"
    ET.SubElement(head, "urlPublic").text = (
        "https://gitgud.io/sjehuda/slixfeed")
    time_stamp = current_time()
    ET.SubElement(head, "dateCreated").text = time_stamp
    ET.SubElement(head, "dateModified").text = time_stamp
    body = ET.SubElement(root, "body")
    for result in results:
        outline = ET.SubElement(body, "outline")
        outline.set("text", result[0])
        outline.set("xmlUrl", result[1])
        # outline.set("type", result[2])
    tree = ET.ElementTree(root)
    tree.write(filename)
