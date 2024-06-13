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
import slixfeed.crawl as crawl
import slixfeed.dt as dt
import slixfeed.fetch as fetch
from slixfeed.log import Logger
import slixfeed.sqlite as sqlite
from slixfeed.url import join_url, trim_url
from slixfeed.utilities import Html, MD, SQLiteMaintain
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
            cache_dir, ext, 'slixfeed_' + dt.timestamp() + '.' + ext)
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
                exist_identifier = sqlite.check_identifier_exist(db_file, identifier)
                if not exist_identifier:
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
                                    updated = dt.convert_struct_time_to_iso8601(updated)
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
                                    feed_updated = dt.convert_struct_time_to_iso8601(feed_updated)
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
                            new_entries = Feed.get_properties_of_entries(
                                jid_bare, db_file, url, feed_id, feed)
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
                            result = await crawl.probe_page(url, document)
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
                    ix = exist_identifier[1]
                    identifier = exist_identifier[2]
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
                link = join_url(url, entry.link)
                link = trim_url(link)
            else:
                link = "*** No link ***"
            if entry.has_key("published"):
                date = entry.published
                date = dt.rfc2822_to_iso8601(date)
            elif entry.has_key("updated"):
                date = entry.updated
                date = dt.rfc2822_to_iso8601(date)
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
            date = dt.rfc2822_to_iso8601(date)
        elif entry.has_key("updated"):
            date = entry.updated
            date = dt.rfc2822_to_iso8601(date)
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
            link = join_url(url, entry.link)
            link = trim_url(link)
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
        Get feed content.
    
        Parameters
        ----------
        db_file : str
            Path to database file.
        url : str, optional
            URL.
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
                feed_updated = dt.convert_struct_time_to_iso8601(feed_updated)
            except:
                feed_updated = ''
        else:
            feed_updated = ''
    
        entries_count = len(feed.entries)
    
        feed_version = feed.version if feed.has_key('version') else ''
        feed_encoding = feed.encoding if feed.has_key('encoding') else ''
        feed_language = feed.feed.language if feed.feed.has_key('language') else ''
        feed_icon = feed.feed.icon if feed.feed.has_key('icon') else ''
        feed_image = feed.feed.image.href if feed.feed.has_key('image') else ''
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
    def get_properties_of_entries(jid_bare, db_file, feed_url, feed_id, feed):
        """
        Get new entries.
    
        Parameters
        ----------
        db_file : str
            Path to database file.
        url : str, optional
            URL.
        """
        # print('MID', feed_url, jid_bare, 'get_properties_of_entries')
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: feed_id: {} url: {}'
                    .format(function_name, feed_id, feed_url))
    
        new_entries = []
        for entry in feed.entries:
            logger.debug('{}: entry: {}'.format(function_name, entry.link))
            if entry.has_key("published"):
                entry_published = entry.published
                entry_published = dt.rfc2822_to_iso8601(entry_published)
            else:
                entry_published = ''
            if entry.has_key("updated"):
                entry_updated = entry.updated
                entry_updated = dt.rfc2822_to_iso8601(entry_updated)
            else:
                entry_updated = dt.now()
            if entry.has_key("link"):
                # link = complete_url(source, entry.link)
                entry_link = join_url(feed_url, entry.link)
                entry_link = trim_url(entry_link)
            else:
                entry_link = feed_url
            # title = feed["feed"]["title"]
            # title = "{}: *{}*".format(feed["feed"]["title"], entry.title)
            entry_title = entry.title if entry.has_key("title") else entry_published
            entry_id = entry.id if entry.has_key("id") else entry_link
            exist = sqlite.check_entry_exist(db_file, feed_id,
                                             identifier=entry_id,
                                             title=entry_title,
                                             link=entry_link,
                                             published=entry_published)
            if not exist:
                read_status = 0
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
                #     media_link = join_url(url, e_link.href)
                #     media_link = trim_url(media_link)
    
                ###########################################################
    
                entry_properties = {
                    "identifier": entry_id,
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
                    "read_status": read_status
                    }
    
                new_entries.extend([{
                    "entry_properties" : entry_properties,
                    "entry_authors" : entry_authors,
                    "entry_contributors" : entry_contributors,
                    "entry_contents" : entry_contents,
                    "entry_links" : entry_links,
                    "entry_tags" : entry_tags
                    }])
                # await sqlite.add_entry(
                #     db_file, title, link, entry_id,
                #     url, date, read_status)
                # await sqlite.set_date(db_file, url)
        return new_entries


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
            urls = sqlite.get_active_feeds_url(db_file)
            for url in urls:
                url = url[0]
                print('sta : ' + url)
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
                    await sqlite.update_feed_status(db_file, feed_id, status_code)
                    document = result['content']
                    feed = parse(document)
                    feed_valid = 0 if feed.bozo else 1
                    await sqlite.update_feed_validity(db_file, feed_id, feed_valid)
                    feed_properties = Feed.get_properties_of_feed(
                        db_file, feed_id, feed)
                    await sqlite.update_feed_properties(
                        db_file, feed_id, feed_properties)
                    new_entries = Feed.get_properties_of_entries(
                        jid_bare, db_file, url, feed_id, feed)
                    if new_entries:
                        print('{}: {} new_entries: {} ({})'.format(jid_bare, len(new_entries), url, feed_id))
                        await sqlite.add_entries_and_update_feed_state(db_file, feed_id, new_entries)
                        await SQLiteMaintain.remove_nonexistent_entries(self, jid_bare, db_file, url, feed)
                # await SQLiteMaintain.remove_nonexistent_entries(self, jid_bare, db_file, url, feed)
                print('end : ' + url)
                # await asyncio.sleep(50)
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
        time_stamp = dt.current_time()
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
