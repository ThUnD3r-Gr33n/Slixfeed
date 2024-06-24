#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

TODO

1) Function scan at "for entry in entries"
   Suppress directly calling function "add_entry" (accept db_file)
   Pass a list of valid entries to a new function "add_entries"
   (accept db_file) which would call function "add_entry" (accept cur).
   * accelerate adding of large set of entries at once.
   * prevent (or mitigate halt of consequent actions).
   * reduce I/O.

2) Call sqlite function from function statistics.
   Returning a list of values doesn't' seem to be a good practice.

3) Special statistics for operator:
   * Size of database(s);
   * Amount of JIDs subscribed;
   * Amount of feeds of all JIDs;
   * Amount of entries of all JIDs.

"""

import asyncio
from feedparser import parse
import os
import slixfeed.config as config
from slixfeed.config import Config
import slixfeed.fetch as fetch
from slixfeed.log import Logger,Message
import slixfeed.sqlite as sqlite
from slixfeed.utilities import DateAndTime, Html, MD, String, Url, Utilities
from slixmpp.xmlstream import ET
import sys
from urllib.parse import urlsplit
import xml.etree.ElementTree as ETR

logger = Logger(__name__)


class Feed:

    # NOTE Consider removal of MD (and any other option HTML and XBEL)
    def export_feeds(jid_bare, ext):
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_bare: {}: ext: {}'.format(function_name, jid_bare, ext))
        cache_dir = config.get_default_cache_directory()
        if not os.path.isdir(cache_dir):
            os.mkdir(cache_dir)
        if not os.path.isdir(cache_dir + '/' + ext):
            os.mkdir(cache_dir + '/' + ext)
        filename = os.path.join(
            cache_dir, ext, 'slixfeed_' + DateAndTime.timestamp() + '.' + ext)
        db_file = config.get_pathname_to_database(jid_bare)
        results = sqlite.get_feeds(db_file)
        match ext:
            # case 'html':
            #     response = 'Not yet implemented.'
            case 'md':
                MD.export_to_markdown(jid_bare, filename, results)
            case 'opml':
                Opml.export_to_file(jid_bare, filename, results)
            # case 'xbel':
            #     response = 'Not yet implemented.'
        return filename


    def pack_entry_into_dict(db_file, entry):
        entry_id = entry[0]
        authors = sqlite.get_authors_by_entry_id(db_file, entry_id)
        entry_authors = []
        for author in authors:
            entry_author = {
                'name': author[2],
                'email': author[3],
                'url': author[4]}
            entry_authors.extend([entry_author])
        contributors = sqlite.get_contributors_by_entry_id(db_file, entry_id)
        entry_contributors = []
        for contributor in contributors:
            entry_contributor = {
                'name': contributor[2],
                'email': contributor[3],
                'url': contributor[4]}
            entry_contributors.extend([entry_contributor])
        links = sqlite.get_links_by_entry_id(db_file, entry_id)
        entry_links = []
        for link in links:
            entry_link = {
                'url': link[2],
                'type': link[3],
                'rel': link[4],
                'size': link[5]}
            entry_links.extend([entry_link])
        tags = sqlite.get_tags_by_entry_id(db_file, entry_id)
        entry_tags = []
        for tag in tags:
            entry_tag = {
                'term': tag[2],
                'scheme': tag[3],
                'label': tag[4]}
            entry_tags.extend([entry_tag])
        contents = sqlite.get_contents_by_entry_id(db_file, entry_id)
        entry_contents = []
        for content in contents:
            entry_content = {
                'text': content[2],
                'type': content[3],
                'base': content[4],
                'lang': content[5]}
            entry_contents.extend([entry_content])
        feed_entry = {
            'authors'      : entry_authors,
            'category'     : entry[10],
            'comments'     : entry[12],
            'contents'     : entry_contents,
            'contributors' : entry_contributors,
            'summary_base' : entry[9],
            'summary_lang' : entry[7],
            'summary_text' : entry[6],
            'summary_type' : entry[8],
            'enclosures'   : entry[13],
            'href'         : entry[11],
            'link'         : entry[3],
            'links'        : entry_links,
            'published'    : entry[14],
            'rating'       : entry[13],
            'tags'         : entry_tags,
            'title'        : entry[4],
            'title_type'   : entry[3],
            'updated'      : entry[15]}
        return feed_entry


    def create_rfc4287_entry(feed_entry):
        node_entry = ET.Element('entry')
        node_entry.set('xmlns', 'http://www.w3.org/2005/Atom')
        # Title
        title = ET.SubElement(node_entry, 'title')
        if feed_entry['title']:
            if feed_entry['title_type']: title.set('type', feed_entry['title_type'])
            title.text = feed_entry['title']
        elif feed_entry['summary_text']:
            if feed_entry['summary_type']: title.set('type', feed_entry['summary_type'])
            title.text = feed_entry['summary_text']
            # if feed_entry['summary_base']: title.set('base', feed_entry['summary_base'])
            # if feed_entry['summary_lang']: title.set('lang', feed_entry['summary_lang'])
        else:
            title.text = feed_entry['published']
        # Some feeds have identical content for contents and summary
        # So if content is present, do not add summary
        if feed_entry['contents']:
            # Content
            for feed_entry_content in feed_entry['contents']:
                content = ET.SubElement(node_entry, 'content')
                # if feed_entry_content['base']: content.set('base', feed_entry_content['base'])
                if feed_entry_content['lang']: content.set('lang', feed_entry_content['lang'])
                if feed_entry_content['type']: content.set('type', feed_entry_content['type'])
                content.text = feed_entry_content['text']
        else:
            # Summary
            summary = ET.SubElement(node_entry, 'summary') # TODO Try 'content'
            # if feed_entry['summary_base']: summary.set('base', feed_entry['summary_base'])
            # TODO Check realization of "lang"
            if feed_entry['summary_type']: summary.set('type', feed_entry['summary_type'])
            if feed_entry['summary_lang']: summary.set('lang', feed_entry['summary_lang'])
            summary.text = feed_entry['summary_text']
        # Authors
        for feed_entry_author in feed_entry['authors']:
            author = ET.SubElement(node_entry, 'author')
            name = ET.SubElement(author, 'name')
            name.text = feed_entry_author['name']
            if feed_entry_author['url']:
                uri = ET.SubElement(author, 'uri')
                uri.text = feed_entry_author['url']
            if feed_entry_author['email']:
                email = ET.SubElement(author, 'email')
                email.text = feed_entry_author['email']
        # Contributors
        for feed_entry_contributor in feed_entry['contributors']:
            contributor = ET.SubElement(node_entry, 'author')
            name = ET.SubElement(contributor, 'name')
            name.text = feed_entry_contributor['name']
            if feed_entry_contributor['url']:
                uri = ET.SubElement(contributor, 'uri')
                uri.text = feed_entry_contributor['url']
            if feed_entry_contributor['email']:
                email = ET.SubElement(contributor, 'email')
                email.text = feed_entry_contributor['email']
        # Category
        category = ET.SubElement(node_entry, "category")
        category.set('category', feed_entry['category'])
        # Tags
        for feed_entry_tag in feed_entry['tags']:
            tag = ET.SubElement(node_entry, 'category')
            tag.set('term', feed_entry_tag['term'])
        # Link
        link = ET.SubElement(node_entry, "link")
        link.set('href', feed_entry['link'])
        # Links
        for feed_entry_link in feed_entry['links']:
            link = ET.SubElement(node_entry, "link")
            link.set('href', feed_entry_link['url'])
            link.set('type', feed_entry_link['type'])
            link.set('rel', feed_entry_link['rel'])
        # Date updated
        if feed_entry['updated']:
            updated = ET.SubElement(node_entry, 'updated')
            updated.text = feed_entry['updated']
        # Date published
        if feed_entry['published']:
            published = ET.SubElement(node_entry, 'published')
            published.text = feed_entry['published']
        return node_entry


    # Look into the type ("atom", "rss2" etc.)
    def is_feed(url, feed):
        """
        Determine whether document is feed or not.
    
        Parameters
        ----------
        feed : dict
            Parsed feed.
    
        Returns
        -------
        val : boolean
            True or False.
        """
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}'.format(function_name))
        value = False
        # message = None
        if not feed.entries:
            if "version" in feed.keys():
                # feed["version"]
                if feed.version:
                    value = True
                    # message = (
                    #     "Empty feed for {}"
                    #     ).format(url)
            elif "title" in feed["feed"].keys():
                value = True
                # message = (
                #     "Empty feed for {}"
                #     ).format(url)
            else:
                value = False
                # message = (
                #     "No entries nor title for {}"
                #     ).format(url)
        elif feed.bozo:
            # NOTE Consider valid even when is not-well-formed
            value = True
            logger.warning('Bozo detected for {}'.format(url))
        else:
            value = True
            # message = (
            #     "Good feed for {}"
            #     ).format(url)
        return value


    async def add_feed(self, jid_bare, db_file, url, identifier):
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: db_file: {} url: {}'
                    .format(function_name, db_file, url))
        while True:
            feed_id = sqlite.get_feed_id(db_file, url)
            if not feed_id:
                if not sqlite.check_identifier_exist(db_file, identifier):
                    result = await fetch.http(url)
                    message = result['message']
                    status_code = result['status_code']
                    if not result['error']:
                        await sqlite.update_feed_status(db_file, feed_id, status_code)
                        document = result['content']
                        feed = parse(document)
                        # if document and status_code == 200:
                        if Feed.is_feed(url, feed):
                            if "title" in feed["feed"].keys():
                                title = feed["feed"]["title"]
                            else:
                                title = urlsplit(url).netloc
                            if "language" in feed["feed"].keys():
                                language = feed["feed"]["language"]
                            else:
                                language = ''
                            if "encoding" in feed.keys():
                                encoding = feed["encoding"]
                            else:
                                encoding = ''
                            if "updated_parsed" in feed["feed"].keys():
                                updated = feed["feed"]["updated_parsed"]
                                try:
                                    updated = DateAndTime.convert_struct_time_to_iso8601(updated)
                                except Exception as e:
                                    logger.error(str(e))
                                    updated = ''
                            else:
                                updated = ''
                            version = feed.version
                            entries_count = len(feed.entries)
                            await sqlite.insert_feed(db_file,
                                                     url,
                                                     title,
                                                     identifier,
                                                     entries=entries_count,
                                                     version=version,
                                                     encoding=encoding,
                                                     language=language,
                                                     status_code=status_code,
                                                     updated=updated)
                            feed_valid = 0 if feed.bozo else 1
                            await sqlite.update_feed_validity(
                                db_file, feed_id, feed_valid)
                            if feed.has_key('updated_parsed'):
                                feed_updated = feed.updated_parsed
                                try:
                                    feed_updated = DateAndTime.convert_struct_time_to_iso8601(feed_updated)
                                except Exception as e:
                                    logger.error(str(e))
                                    feed_updated = None
                            else:
                                feed_updated = None
                            feed_properties = Feed.get_properties_of_feed(
                                db_file, feed_id, feed)
                            await sqlite.update_feed_properties(
                                db_file, feed_id, feed_properties)
                            feed_id = sqlite.get_feed_id(db_file, url)
                            feed_id = feed_id[0]
                            new_entries = []
                            for entry in feed.entries:
                                if entry.has_key("link"):
                                    entry_link = Url.join_url(url, entry.link)
                                    entry_link = Url.trim_url(entry_link)
                                    entry_identifier = String.md5_hash(entry_link)
                                    if not sqlite.get_entry_id_by_identifier(
                                            db_file, entry_identifier):
                                        new_entry = Feed.get_properties_of_entry(
                                            url, entry_identifier, entry)
                                        new_entries.extend([new_entry])
                            if new_entries:
                                await sqlite.add_entries_and_update_feed_state(
                                    db_file, feed_id, new_entries)
                            old = Config.get_setting_value(self.settings, jid_bare, 'old')
                            if not old: await sqlite.mark_feed_as_read(db_file, feed_id)
                            result_final = {'link' : url,
                                            'index' : feed_id,
                                            'name' : title,
                                            'code' : status_code,
                                            'error' : False,
                                            'message': message,
                                            'exist' : False,
                                            'identifier' : None}
                            break
                        else:
                            # NOTE Do not be tempted to return a compact dictionary.
                            #      That is, dictionary within dictionary
                            #      Return multiple dictionaries in a list or tuple.
                            result = await FeedDiscovery.probe_page(url, document)
                            if not result:
                                # Get out of the loop with dict indicating error.
                                result_final = {'link' : url,
                                                'index' : None,
                                                'name' : None,
                                                'code' : status_code,
                                                'error' : True,
                                                'message': message,
                                                'exist' : False,
                                                'identifier' : None}
                                break
                            elif isinstance(result, list):
                                # Get out of the loop and deliver a list of dicts.
                                result_final = result
                                break
                            else:
                                # Go back up to the while loop and try again.
                                url = result['link']
                    else:
                        await sqlite.update_feed_status(db_file, feed_id, status_code)
                        result_final = {'link' : url,
                                        'index' : None,
                                        'name' : None,
                                        'code' : status_code,
                                        'error' : True,
                                        'message': message,
                                        'exist' : False,
                                        'identifier' : None}
                        break
                else:
                    ix = sqlite.get_entry_id_by_identifier(db_file, identifier)
                    message = ('Identifier "{}" is already allocated.'
                               .format(identifier))
                    result_final = {'link' : url,
                                    'index' : ix,
                                    'name' : None,
                                    'code' : None,
                                    'error' : False,
                                    'message': message,
                                    'exist' : False,
                                    'identifier' : identifier}
                    break
            else:
                feed_id = feed_id[0]
                title = sqlite.get_feed_title(db_file, feed_id)
                title = title[0]
                message = 'URL already exist.'
                result_final = {'link' : url,
                                'index' : feed_id,
                                'name' : title,
                                'code' : None,
                                'error' : False,
                                'message': message,
                                'exist' : True,
                                'identifier' : None}
                break
        return result_final


    def view_feed(url, feed):
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: url: {}'
                     .format(function_name, url))
        if "title" in feed["feed"].keys():
            title = feed["feed"]["title"]
        else:
            title = urlsplit(url).netloc
        entries = feed.entries
        response = "Preview of {}:\n\n```\n".format(title)
        counter = 0
        for entry in entries:
            counter += 1
            if entry.has_key("title"):
                title = entry.title
            else:
                title = "*** No title ***"
            if entry.has_key("link"):
                # link = complete_url(source, entry.link)
                link = Url.join_url(url, entry.link)
                link = Url.trim_url(link)
            else:
                link = "*** No link ***"
            if entry.has_key("published"):
                date = entry.published
                date = DateAndTime.rfc2822_to_iso8601(date)
            elif entry.has_key("updated"):
                date = entry.updated
                date = DateAndTime.rfc2822_to_iso8601(date)
            else:
                date = "*** No date ***"
            response += ("Title : {}\n"
                         "Date  : {}\n"
                         "Link  : {}\n"
                         "Count : {}\n"
                         "\n"
                         .format(title, date, link, counter))
            if counter > 4:
                break
        response += (
            "```\nSource: {}"
            ).format(url)
        return response


    def view_entry(url, feed, num):
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: url: {} num: {}'
                    .format(function_name, url, num))
        if "title" in feed["feed"].keys():
            title = feed["feed"]["title"]
        else:
            title = urlsplit(url).netloc
        entries = feed.entries
        num = int(num) - 1
        entry = entries[num]
        response = "Preview of {}:\n\n```\n".format(title)
        if entry.has_key("title"):
            title = entry.title
        else:
            title = '*** No title ***'
        if entry.has_key("published"):
            date = entry.published
            date = DateAndTime.rfc2822_to_iso8601(date)
        elif entry.has_key("updated"):
            date = entry.updated
            date = DateAndTime.rfc2822_to_iso8601(date)
        else:
            date = '*** No date ***'
        if entry.has_key("summary"):
            summary = entry.summary
            # Remove HTML tags
            if summary:
                summary = Html.remove_html_tags(summary)
                # TODO Limit text length
                summary = summary.replace("\n\n\n", "\n\n")
            else:
                summary = '*** No summary ***'
        else:
            summary = '*** No summary ***'
        if entry.has_key("link"):
            # link = complete_url(source, entry.link)
            link = Url.join_url(url, entry.link)
            link = Url.trim_url(link)
        else:
            link = '*** No link ***'
        response = ("{}\n"
                    "\n"
                    # "> {}\n"
                    "{}\n"
                    "\n"
                    "{}\n"
                    "\n"
                    .format(title, summary, link))
        return response


    # NOTE This function is not being utilized
    async def download_feed(self, db_file, feed_url):
        """
        Process feed content.
    
        Parameters
        ----------
        db_file : str
            Path to database file.
        feed_url : str
            URL of feed.
        """
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: db_file: {} url: {}'
                    .format(function_name, db_file, feed_url))
        if isinstance(feed_url, tuple): feed_url = feed_url[0]
        result = await fetch.http(feed_url)
        feed_id = sqlite.get_feed_id(db_file, feed_url)
        feed_id = feed_id[0]
        status_code = result['status_code']
        await sqlite.update_feed_status(db_file, feed_id, status_code)


    def get_properties_of_feed(db_file, feed_id, feed):
    
        if feed.has_key('updated_parsed'):
            feed_updated = feed.updated_parsed
            try:
                feed_updated = DateAndTime.convert_struct_time_to_iso8601(feed_updated)
            except:
                feed_updated = ''
        else:
            feed_updated = ''
    
        entries_count = len(feed.entries)
    
        feed_version = feed.version if feed.has_key('version') else ''
        feed_encoding = feed.encoding if feed.has_key('encoding') else ''
        feed_language = feed.feed.language if feed.feed.has_key('language') else ''
        feed_icon = feed.feed.icon if feed.feed.has_key('icon') else ''
        # (Pdb) feed.feed.image
        # {}
        # (Pdb) feed.version
        # 'rss10'
        # (Pdb) feed.feed.image
        # {'links': [{'rel': 'alternate', 'type': 'text/html'}]}
        # (Pdb) feed.version
        # ''
        feed_image = feed.feed.image.href if feed.feed.has_key('image') and feed.feed.image.has_key('href') else ''
        feed_logo = feed.feed.logo if feed.feed.has_key('logo') else ''
        feed_ttl = feed.feed.ttl if feed.feed.has_key('ttl') else ''
    
        feed_properties = {
            "version" : feed_version,
            "encoding" : feed_encoding,
            "language" : feed_language,
            "rating" : '',
            "entries_count" : entries_count,
            "icon" : feed_icon,
            "image" : feed_image,
            "logo" : feed_logo,
            "ttl" : feed_ttl,
            "updated" : feed_updated,
            }
    
        return feed_properties


    # TODO get all active feeds of active accounts and scan the feed with the earliest scanned time
    # TODO Rename function name (idea: scan_and_populate)
    def get_properties_of_entry(feed_url, entry_identifier, entry):
        """
        Process entry content.
    
        Parameters
        ----------
        feed_url : str
            URL of feed.
        entry : 
            Object of entry.
        """
        function_name = sys._getframe().f_code.co_name
        logger.debug('{} feed_url: {}'
                    .format(function_name, feed_url))
    
        read_status = 0
        if entry.has_key("published"):
            entry_published = entry.published
            entry_published = DateAndTime.rfc2822_to_iso8601(entry_published)
        else:
            entry_published = ''
        if entry.has_key("updated"):
            entry_updated = entry.updated
            entry_updated = DateAndTime.rfc2822_to_iso8601(entry_updated)
        else:
            entry_updated = DateAndTime.now()
        if entry.has_key("link"):
            # link = complete_url(source, entry.link)
            entry_link = Url.join_url(feed_url, entry.link)
            entry_link = Url.trim_url(entry_link)
        else:
            entry_link = feed_url
        # title = feed["feed"]["title"]
        # title = "{}: *{}*".format(feed["feed"]["title"], entry.title)
        entry_title = entry.title if entry.has_key("title") else entry_published
        # entry_id = entry.id if entry.has_key("id") else entry_link
        # # Filter
        # pathname = urlsplit(link).path
        # string = (
        #     "{} {} {}"
        #     ).format(
        #         title, summary, pathname)
        # if self.settings['default']['filter']:
        #     print('Filter is now processing data.')
        #     allow_list = config.is_include_keyword(db_file,
        #                                            "allow", string)
        #     if not allow_list:
        #         reject_list = config.is_include_keyword(db_file,
        #                                                 "deny",
        #                                                 string)
        #         if reject_list:
        #             read_status = 1
        #             logger.debug('Rejected : {}'
        #                          '\n'
        #                          'Keyword  : {}'
        #                          .format(link, reject_list))
        if isinstance(entry_published, int):
            logger.error('Variable "published" is int: {}'.format(entry_published))
        if isinstance(entry_updated, int):
            logger.error('Variable "updated" is int: {}'.format(entry_updated))

        # Authors
        entry_authors =[]
        if entry.has_key('authors'):
            for author in entry.authors:
                author_properties = {
                    'name' : author.name if author.has_key('name') else '',
                    'url' : author.href if author.has_key('href') else '',
                    'email' : author.email if author.has_key('email') else '',
                    }
                entry_authors.extend([author_properties])
        elif entry.has_key('author_detail'):
            author_properties = {
                'name' : entry.author_detail.name if entry.author_detail.has_key('name') else '',
                'url' : entry.author_detail.href if entry.author_detail.has_key('href') else '',
                'email' : entry.author_detail.email if entry.author_detail.has_key('email') else '',
                }
            entry_authors.extend([author_properties])
        elif entry.has_key('author'):
            author_properties = {
                'name' : entry.author,
                'url' : '',
                'email' : '',
                }
            entry_authors.extend([author_properties])

        # Contributors
        entry_contributors = []
        if entry.has_key('contributors'):
            for contributor in entry.contributors:
                contributor_properties = {
                    'name' : contributor.name if contributor.has_key('name') else '',
                    'url' : contributor.href if contributor.has_key('href') else '',
                    'email' : contributor.email if contributor.has_key('email') else '',
                    }
                entry_contributors.extend([contributor_properties])

        # Tags
        entry_tags = []
        if entry.has_key('tags'):
            for tag in entry.tags:
                tag_properties = {
                    'term' : tag.term if tag.has_key('term') else '',
                    'scheme' : tag.scheme if tag.has_key('scheme') else '',
                    'label' : tag.label if tag.has_key('label') else '',
                    }
                entry_tags.extend([tag_properties])

        # Content
        entry_contents = []
        if entry.has_key('content'):
            for content in entry.content:
                text = content.value if content.has_key('value') else ''
                type = content.type if content.has_key('type') else ''
                lang = content.lang if content.has_key('lang') else ''
                base = content.base if content.has_key('base') else ''
                entry_content = {
                    'text' : text,
                    'lang' : lang,
                    'type' : type,
                    'base' : base,
                    }
                entry_contents.extend([entry_content])

        # Links and Enclosures
        entry_links = []
        if entry.has_key('links'):
            for link in entry.links:
                link_properties = {
                    'url' : link.href if link.has_key('href') else '',
                    'rel' : link.rel if link.has_key('rel') else '',
                    'type' : link.type if link.has_key('type') else '',
                    'length' : '',
                    }
                entry_links.extend([link_properties])
        # Element media:content is utilized by Mastodon
        if entry.has_key('media_content'):
            for link in entry.media_content:
                link_properties = {
                    'url' : link['url'] if 'url' in link else '',
                    'rel' : 'enclosure',
                    'type' : link['type'] if 'type' in link else '',
                    # 'medium' : link['medium'] if 'medium' in link else '',
                    'length' : link['filesize'] if 'filesize' in link else '',
                    }
                entry_links.extend([link_properties])
        if entry.has_key('media_thumbnail'):
            for link in entry.media_thumbnail:
                link_properties = {
                    'url' : link['url'] if 'url' in link else '',
                    'rel' : 'enclosure',
                    'type' : '',
                    # 'medium' : 'image',
                    'length' : '',
                    }
                entry_links.extend([link_properties])

        # Category
        entry_category = entry.category if entry.has_key('category') else ''

        # Comments
        entry_comments = entry.comments if entry.has_key('comments') else ''

        # href
        entry_href = entry.href if entry.has_key('href') else ''

        # Link: Same as entry.links[0].href in most if not all cases
        entry_link = entry.link if entry.has_key('link') else ''

        # Rating
        entry_rating = entry.rating if entry.has_key('rating') else ''

        # Summary
        entry_summary_text = entry.summary if entry.has_key('summary') else ''
        if entry.has_key('summary_detail'):
            entry_summary_type = entry.summary_detail.type if entry.summary_detail.has_key('type') else ''
            entry_summary_lang = entry.summary_detail.lang if entry.summary_detail.has_key('lang') else ''
            entry_summary_base = entry.summary_detail.base if entry.summary_detail.has_key('base') else ''
        else:
            entry_summary_type = ''
            entry_summary_lang = ''
            entry_summary_base = ''

        # Title
        entry_title = entry.title if entry.has_key('title') else ''
        if entry.has_key('title_detail'):
            entry_title_type = entry.title_detail.type if entry.title_detail.has_key('type') else ''
        else:
            entry_title_type = ''

        ###########################################################

        # media_type = e_link.type[:e_link.type.index("/")]
        # if (e_link.rel == "enclosure" and
        #     media_type in ("audio", "image", "video")):
        #     media_link = e_link.href
        #     media_link = Url.join_url(url, e_link.href)
        #     media_link = Url.trim_url(media_link)

        ###########################################################

        entry_properties = {
            "identifier": entry_identifier,
            "link": entry_link,
            "href": entry_href,
            "title": entry_title,
            "title_type": entry_title_type,
            'summary_text' : entry_summary_text,
            'summary_lang' : entry_summary_lang,
            'summary_type' : entry_summary_type,
            'summary_base' : entry_summary_base,
            'category' : entry_category,
            "comments": entry_comments,
            "rating": entry_rating,
            "published": entry_published,
            "updated": entry_updated,
            "read_status": read_status}

        new_entry = {
            "entry_properties" : entry_properties,
            "entry_authors" : entry_authors,
            "entry_contributors" : entry_contributors,
            "entry_contents" : entry_contents,
            "entry_links" : entry_links,
            "entry_tags" : entry_tags}
        # await sqlite.add_entry(
        #     db_file, title, link, entry_id,
        #     url, date, read_status)
        # await sqlite.set_date(db_file, url)
        return new_entry


"""

FIXME

1) https://wiki.pine64.org
     File "/slixfeed/crawl.py", line 178, in feed_mode_guess
       address = Url.join_url(url, parted_url.path.split('/')[1] + path)
                               ~~~~~~~~~~~~~~~~~~~~~~~~~~^^^
   IndexError: list index out of range

TODO

1.1) Attempt to scan more paths: /blog/, /news/ etc., including root / 
   Attempt to scan sub domains
   https://esmailelbob.xyz/en/
   https://blog.esmailelbob.xyz/feed/

1.2) Consider utilizing fetch.http_response

2) DeviantArt
   https://www.deviantart.com/nedesem/gallery
   https://backend.deviantart.com/rss.xml?q=gallery:nedesem
   https://backend.deviantart.com/rss.xml?q=nedesem

   https://www.deviantart.com/search?q=
   https://backend.deviantart.com/rss.xml?q=search:

FEEDS CRAWLER PROJECT

3) Mark redirects for manual check

Title : JSON Feed
Link  : https://www.jsonfeed.org/feed.json.xml

Title : JSON Feed
Link  : https://www.jsonfeed.org/feed.json/atom.xml

Title : JSON Feed
Link  : https://www.jsonfeed.org/feed.json/feed.xml

Title : JSON Feed
Link  : https://www.jsonfeed.org/feed.json/feeds/rss/news.xml.php

Title : JSON Feed
Link  : https://www.jsonfeed.org/feed.json/jekyll/feed.xml

Title : JSON Feed
Link  : https://www.jsonfeed.org/feed.json/news.xml

Title : JSON Feed
Link  : https://www.jsonfeed.org/feed.json/news.xml.php

Title : JSON Feed
Link  : https://www.jsonfeed.org/feed.json/rdf.xml

Title : JSON Feed
Link  : https://www.jsonfeed.org/feed.json/rss.xml

Title : JSON Feed
Link  : https://www.jsonfeed.org/feed.json/videos.xml


"""

from aiohttp import ClientError, ClientSession, ClientTimeout
from lxml import etree
from lxml import html
from lxml.etree import fromstring


class FeedDiscovery:


# TODO Use boolean as a flag to determine whether a single URL was found
# async def probe_page(
#     callback, url, document, num=None, db_file=None):
#     result = None
#     try:
#         # tree = etree.fromstring(res[0]) # etree is for xml
#         tree = html.fromstring(document)
#     except:
#         result = (
#             "> {}\nFailed to parse URL as feed."
#             ).format(url)
#     if not result:
#         print("RSS Auto-Discovery Engaged")
#         result = await feed_mode_auto_discovery(url, tree)
#     if not result:
#         print("RSS Scan Mode Engaged")
#         result = await feed_mode_scan(url, tree)
#     if not result:
#         print("RSS Arbitrary Mode Engaged")
#         result = await feed_mode_request(url, tree)
#     if not result:
#         result = (
#             "> {}\nNo news feeds were found for URL."
#             ).format(url)
#     # elif msg:
#     else:
#         if isinstance(result, str):
#             return result
#         elif isinstance(result, list):
#             url = result[0]
#             if db_file:
#                 # print("if db_file", db_file)
#                 return await callback(db_file, url)
#             elif num:
#                 return await callback(url, num)
#             else:
#                 return await callback(url)

    async def probe_page(url, document=None):
        """
        Parameters
        ----------
        url : str
            URL.
        document : TYPE
            DESCRIPTION.
    
        Returns
        -------
        result : list or str
            Single URL as list or selection of URLs as str.
        """
        if not document:
            response = await fetch.http(url)
            if not response['error']:
                document = response['content']
        try:
            # tree = etree.fromstring(res[0]) # etree is for xml
            tree = html.fromstring(document)
            result = None
        except Exception as e:
            logger.error(str(e))
            try:
                # /questions/15830421/xml-unicode-strings-with-encoding-declaration-are-not-supported
                # xml = html.fromstring(document.encode('utf-8'))
                # parser = etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')
                # tree = fromstring(xml, parser=parser)
    
                # /questions/57833080/how-to-fix-unicode-strings-with-encoding-declaration-are-not-supported
                #tree = html.fromstring(bytes(document, encoding='utf8'))
    
                # https://twigstechtips.blogspot.com/2013/06/python-lxml-strings-with-encoding.html
                #parser = etree.XMLParser(recover=True)
                #tree = etree.fromstring(document, parser)
    
                tree = html.fromstring(document.encode('utf-8'))
                result = None
            except Exception as e:
                logger.error(str(e))
                logger.warning("Failed to parse URL as feed for {}.".format(url))
                result = {'link' : None,
                          'index' : None,
                          'name' : None,
                          'code' : None,
                          'error' : True,
                          'exist' : None}
        if not result:
            logger.debug("Feed auto-discovery engaged for {}".format(url))
            result = FeedDiscovery.feed_mode_auto_discovery(url, tree)
        if not result:
            logger.debug("Feed link scan mode engaged for {}".format(url))
            result = FeedDiscovery.feed_mode_scan(url, tree)
        if not result:
            logger.debug("Feed arbitrary mode engaged for {}".format(url))
            result = FeedDiscovery.feed_mode_guess(url, tree)
        if not result:
            logger.debug("No feeds were found for {}".format(url))
            result = None
        result = await FeedDiscovery.process_feed_selection(url, result)
        return result
    
    
    # TODO Improve scan by gradual decreasing of path
    def feed_mode_guess(url, tree):
        """
        Lookup for feeds by pathname using HTTP Requests.
    
        Parameters
        ----------
        db_file : str
            Path to database file.
        url : str
            URL.
        tree : TYPE
            DESCRIPTION.
    
        Returns
        -------
        msg : str
            Message with URLs.
        """
        urls = []
        parted_url = urlsplit(url)
        paths = config.open_config_file("lists.toml")["pathnames"]
        # Check whether URL has path (i.e. not root)
        # Check parted_url.path to avoid error in case root wasn't given
        # TODO Make more tests
        if parted_url.path and parted_url.path.split('/')[1]:
            paths.extend(
                [".atom", ".feed", ".rdf", ".rss"]
                ) if '.rss' not in paths else -1
            # if paths.index('.rss'):
            #     paths.extend([".atom", ".feed", ".rdf", ".rss"])
        parted_url_path = parted_url.path if parted_url.path else '/'
        for path in paths:
            address = Url.join_url(url, parted_url_path.split('/')[1] + path)
            if address not in urls:
                urls.extend([address])
        # breakpoint()
        # print("feed_mode_guess")
        return urls
    
    
    def feed_mode_scan(url, tree):
        """
        Scan page for potential feeds by pathname.
    
        Parameters
        ----------
        db_file : str
            Path to database file.
        url : str
            URL.
        tree : TYPE
            DESCRIPTION.
    
        Returns
        -------
        msg : str
            Message with URLs.
        """
        urls = []
        paths = config.open_config_file("lists.toml")["pathnames"]
        for path in paths:
            # xpath_query = "//*[@*[contains(.,'{}')]]".format(path)
            # xpath_query = "//a[contains(@href,'{}')]".format(path)
            num = 5
            xpath_query = (
                "(//a[contains(@href,'{}')])[position()<={}]"
                ).format(path, num)
            addresses = tree.xpath(xpath_query)
            xpath_query = (
                "(//a[contains(@href,'{}')])[position()>last()-{}]"
                ).format(path, num)
            addresses += tree.xpath(xpath_query)
            # NOTE Should number of addresses be limited or
            # perhaps be N from the start and N from the end
            for address in addresses:
                address = Url.join_url(url, address.xpath('@href')[0])
                if address not in urls:
                    urls.extend([address])
        # breakpoint()
        # print("feed_mode_scan")
        return urls
    
    
    def feed_mode_auto_discovery(url, tree):
        """
        Lookup for feeds using RSS autodiscovery technique.
    
        See: https://www.rssboard.org/rss-autodiscovery
    
        Parameters
        ----------
        db_file : str
            Path to database file.
        url : str
            URL.
        tree : TYPE
            DESCRIPTION.
    
        Returns
        -------
        msg : str
            Message with URLs.
        """
        xpath_query = (
            '//link[(@rel="alternate") and '
            '(@type="application/atom+xml" or '
            '@type="application/rdf+xml" or '
            '@type="application/rss+xml")]'
            )
        # xpath_query = """//link[(@rel="alternate") and (@type="application/atom+xml" or @type="application/rdf+xml" or @type="application/rss+xml")]/@href"""
        # xpath_query = "//link[@rel='alternate' and @type='application/atom+xml' or @rel='alternate' and @type='application/rss+xml' or @rel='alternate' and @type='application/rdf+xml']/@href"
        feeds = tree.xpath(xpath_query)
        if feeds:
            urls = []
            for feed in feeds:
                # # The following code works;
                # # The following code will catch
                # # only valid resources (i.e. not 404);
                # # The following code requires more bandwidth.
                # res = await fetch.http(feed)
                # if res[0]:
                #     disco = parse(res[0])
                #     title = disco["feed"]["title"]
                #     msg += "{} \n {} \n\n".format(title, feed)
    
                # feed_name = feed.xpath('@title')[0]
                # feed_addr = Url.join_url(url, feed.xpath('@href')[0])
    
                # if feed_addr.startswith("/"):
                #     feed_addr = url + feed_addr
                address = Url.join_url(url, feed.xpath('@href')[0])
                if address not in urls:
                    urls.extend([address])
            # breakpoint()
            # print("feed_mode_auto_discovery")
            return urls
    
    
    # TODO Segregate function into function that returns
    # URLs (string) and Feeds (dict) and function that
    # composes text message (string).
    # Maybe that's not necessary.
    async def process_feed_selection(url, urls):
        feeds = {}
        for i in urls:
            result = await fetch.http(i)
            if not result['error']:
                document = result['content']
                status_code = result['status_code']
                if status_code == 200: # NOTE This line might be redundant
                    try:
                        feeds[i] = [parse(document)]
                    except:
                        continue
        message = (
            "Web feeds found for {}\n\n```\n"
            ).format(url)
        urls = []
        for feed_url in feeds:
            # try:
            #     res = await fetch.http(feed)
            # except:
            #     continue
            feed_name = None
            if "title" in feeds[feed_url][0]["feed"].keys():
                feed_name = feeds[feed_url][0].feed.title
            feed_name = feed_name if feed_name else "Untitled"
            # feed_name = feed_name if feed_name else urlsplit(feed_url).netloc
            # AttributeError: 'str' object has no attribute 'entries'
            if "entries" in feeds[feed_url][0].keys():
                feed_amnt = feeds[feed_url][0].entries
            else:
                continue
            if feed_amnt:
                # NOTE Because there could be many false positives
                #      which are revealed in second phase of scan, we
                #      could end with a single feed, which would be
                #      listed instead of fetched, so feed_url_mark is
                #      utilized in order to make fetch possible.
                # NOTE feed_url_mark was a variable which stored
                #      single URL (probably first accepted as valid)
                #      in order to get an indication whether a single
                #      URL has been fetched, so that the receiving
                #      function will scan that single URL instead of
                #      listing it as a message.
                url = {'link' : feed_url,
                       'index' : None,
                       'name' : feed_name,
                       'code' : status_code,
                       'error' : False,
                       'exist' : None}
                urls.extend([url])
        count = len(urls)
        if count > 1:
            result = urls
        elif count:
            result = urls[0]
        else:
            result = None
        return result
    
    
    # def get_discovered_feeds(url, urls):
    #     message = (
    #         "Found {} web feeds:\n\n```\n"
    #         ).format(len(urls))
    #     if len(urls) > 1:
    #         for urls in urls:
    #                 message += (
    #                     "Title : {}\n"
    #                     "Link  : {}\n"
    #                     "\n"
    #                     ).format(url, url.title)
    #         message += (
    #             "```\nThe above feeds were extracted from\n{}"
    #             ).format(url)
    #     elif len(urls) > 0:
    #         result = urls
    #     else:
    #         message = (
    #             "No feeds were found for {}"
    #             ).format(url)
    #     return result
    
    
    # Test module
    # TODO ModuleNotFoundError: No module named 'slixfeed'
    # import slixfeed.fetch as fetch
    # from slixfeed.action import is_feed, process_feed_selection
    
    # async def start(url):
    #     while True:
    #         result = await fetch.http(url)
    #         document = result[0]
    #         status = result[1]
    #         if document:
    #             feed = parse(document)
    #             if is_feed(feed):
    #                 print(url)
    #             else:
    #                 urls = await probe_page(
    #                     url, document)
    #                 if len(urls) > 1:
    #                     await process_feed_selection(urls)
    #                 elif urls:
    #                     url = urls[0]
    #         else:
    #             response = (
    #                 "> {}\nFailed to load URL.  Reason: {}"
    #                 ).format(url, status)
    #             break
    #     return response
    
    # url = "https://www.smh.com.au/rssheadlines"
    # start(url)





class FeedTask:


    # TODO Take this function out of
    # <class 'slixmpp.clientxmpp.ClientXMPP'>
    async def check_updates(self, jid_bare):
        """
        Start calling for update check up.
    
        Parameters
        ----------
        jid : str
            Jabber ID.
        """
        # print('Scanning for updates for JID {}'.format(jid_bare))
        logger.info('Scanning for updates for JID {}'.format(jid_bare))
        while True:
            db_file = config.get_pathname_to_database(jid_bare)
            urls = sqlite.get_active_feeds_url_sorted_by_last_scanned(db_file)
            for url in urls:
                Message.printer('Scanning updates for URL {} ...'.format(url))
                url = url[0]
                # print('STA',url)
                
                # # Skip Reddit
                # if 'reddit.com' in str(url).lower():
                #     print('Reddit Atom Syndication feeds are not supported by Slixfeed.')
                #     print('Skipping URL:', url)
                #     continue
    
                result = await fetch.http(url)
                status_code = result['status_code']
                feed_id = sqlite.get_feed_id(db_file, url)
                feed_id = feed_id[0]
                if not result['error']:
                    identifier = sqlite.get_feed_identifier(db_file, feed_id)
                    identifier = identifier[0]
                    if not identifier:
                        counter = 0
                        while True:
                            identifier = String.generate_identifier(url, counter)
                            if sqlite.check_identifier_exist(db_file, identifier):
                                counter += 1
                            else:
                                break
                        await sqlite.update_feed_identifier(db_file, feed_id, identifier)
                        # identifier = sqlite.get_feed_identifier(db_file, feed_id)
                        # identifier = identifier[0]
                    await sqlite.update_feed_status(db_file, feed_id, status_code)
                    document = result['content']
                    feed = parse(document)
                    feed_valid = 0 if feed.bozo else 1
                    await sqlite.update_feed_validity(db_file, feed_id, feed_valid)
                    feed_properties = Feed.get_properties_of_feed(
                        db_file, feed_id, feed)
                    await sqlite.update_feed_properties(
                        db_file, feed_id, feed_properties)
                    new_entries = []
                    for entry in feed.entries:
                        if entry.has_key("link"):
                            # link = complete_url(source, entry.link)
                            entry_link = Url.join_url(url, entry.link)
                            entry_link = Url.trim_url(entry_link)
                            entry_identifier = String.md5_hash(entry_link)
                            # if 'f-droid.org' in url:
                            #     breakpoint()
                            #     print(entry.link)
                            #     print(entry_identifier)
                            # Check if an entry identifier exists
                            if not sqlite.get_entry_id_by_identifier(
                                    db_file, entry_identifier):
                                new_entry = Feed.get_properties_of_entry(
                                    url, entry_identifier, entry)
                                # new_entries.append(new_entry)
                                new_entries.extend([new_entry])
                    if new_entries:
                        await sqlite.add_entries_and_update_feed_state(db_file, feed_id, new_entries)
                        limit = Config.get_setting_value(self.settings, jid_bare, 'archive')
                        ixs = sqlite.get_entries_id_of_feed(db_file, feed_id)
                        ixs_invalid = {}
                        for ix in ixs:
                            ix = ix[0]
                            read_status = sqlite.is_entry_read(db_file, ix)
                            read_status = read_status[0]
                            entry_identifier_local = sqlite.get_entry_identifier(db_file, ix)
                            entry_identifier_local = entry_identifier_local[0]
                            valid = False
                            for entry in feed.entries:
                                if entry.has_key("link"):
                                    entry_link = Url.join_url(url, entry.link)
                                    entry_link = Url.trim_url(entry_link)
                                    entry_identifier_external = Utilities.hash_url_to_md5(
                                        entry_link)
                                    if entry_identifier_local == entry_identifier_external:
                                        valid = True
                                        continue
                            if not valid: ixs_invalid[ix] = read_status
                        if len(ixs_invalid):
                            await sqlite.process_invalid_entries(db_file, ixs_invalid)
                        # TODO return number of archived entries and add if statement to run archive maintainence function
                        await sqlite.maintain_archive(db_file, limit)
                # await sqlite.process_invalid_entries(db_file, ixs)
                await asyncio.sleep(60 * 2)
            val = Config.get_setting_value(self.settings, jid_bare, 'check')
            await asyncio.sleep(60 * float(val))
            # Schedule to call this function again in 90 minutes
            # loop.call_at(
            #     loop.time() + 60 * 90,
            #     loop.create_task,
            #     self.check_updates(jid)
            # )


    def restart_task(self, jid_bare):
        if jid_bare == self.boundjid.bare:
            return
        if jid_bare not in self.task_manager:
            self.task_manager[jid_bare] = {}
            logger.info('Creating new task manager for JID {}'.format(jid_bare))
        logger.info('Stopping task "check" for JID {}'.format(jid_bare))
        try:
            self.task_manager[jid_bare]['check'].cancel()
        except:
            logger.info('No task "check" for JID {} (FeedTask.check_updates)'
                        .format(jid_bare))
        logger.info('Starting tasks "check" for JID {}'.format(jid_bare))
        self.task_manager[jid_bare]['check'] = asyncio.create_task(
            FeedTask.check_updates(self, jid_bare))


class Opml:


    # TODO Consider adding element jid as a pointer of import
    def export_to_file(jid, filename, results):
        # print(jid, filename, results)
        function_name = sys._getframe().f_code.co_name
        logger.debug('{} jid: {} filename: {}'
                    .format(function_name, jid, filename))
        root = ETR.Element("opml")
        root.set("version", "1.0")
        head = ETR.SubElement(root, "head")
        ETR.SubElement(head, "title").text = "{}".format(jid)
        ETR.SubElement(head, "description").text = (
            "Set of subscriptions exported by Slixfeed")
        ETR.SubElement(head, "generator").text = "Slixfeed"
        ETR.SubElement(head, "urlPublic").text = (
            "https://slixfeed.woodpeckersnest.space/")
        time_stamp = DateAndTime.current_time()
        ETR.SubElement(head, "dateCreated").text = time_stamp
        ETR.SubElement(head, "dateModified").text = time_stamp
        body = ETR.SubElement(root, "body")
        for result in results:
            outline = ETR.SubElement(body, "outline")
            outline.set("text", result[1])
            outline.set("xmlUrl", result[2])
            # outline.set("type", result[2])
        tree = ETR.ElementTree(root)
        tree.write(filename)


    async def import_from_file(db_file, result):
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: db_file: {}'
                    .format(function_name, db_file))
        if not result['error']:
            document = result['content']
            root = ETR.fromstring(document)
            before = sqlite.get_number_of_items(db_file, 'feeds_properties')
            feeds = []
            for child in root.findall(".//outline"):
                url = child.get("xmlUrl")
                title = child.get("text")
                # feed = (url, title)
                # feeds.extend([feed])
                feed = {
                    'title' : title,
                    'url' : url,
                    }
                feeds.extend([feed])
            await sqlite.import_feeds(db_file, feeds)
            await sqlite.add_metadata(db_file)
            after = sqlite.get_number_of_items(db_file, 'feeds_properties')
            difference = int(after) - int(before)
            return difference
