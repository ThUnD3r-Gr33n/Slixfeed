#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from slixfeed.log import Logger
import slixfeed.dt as dt
import slixfeed.sqlite as sqlite
import sys
import xml.etree.ElementTree as ETR

logger = Logger(__name__)

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
            "https://gitgud.io/sjehuda/slixfeed")
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
