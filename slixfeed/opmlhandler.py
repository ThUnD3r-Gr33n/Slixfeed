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

"""

import listparser
import lxml

import sqlitehandler
import datahandler

async def import_opml(db_file, opml_doc):
    feeds = listparser.parse(opml_doc)['feeds']
    for feed in feeds:
        url = feed['url']
        title = feed['title']
        # categories = feed['categories']
        # tags = feed['tags']
        await datahandler.add_feed_no_check(db_file, [url, title])
    

# NOTE Use OPyML or LXML
async def export_opml():
    result = await sqlitehandler.get_feeds()
