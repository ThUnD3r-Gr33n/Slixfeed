#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import slixfeed.fetch as fetch
from slixfeed.log import Logger
import sys
from urllib.parse import parse_qs, urlsplit

logger = Logger(__name__)

class BitTorrent:

    # TODO Add support for eDonkey, Gnutella, Soulseek
    async def get_magnet(link):
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: {}'.format(function_name, link))
        parted_link = urlsplit(link)
        queries = parse_qs(parted_link.query)
        query_xt = queries["xt"][0]
        if query_xt.startswith("urn:btih:"):
            filename = queries["dn"][0]
            checksum = query_xt[len("urn:btih:"):]
            torrent = await fetch.magnet(link)
            logger.debug('Attempting to retrieve {} ({})'
                         .format(filename, checksum))
            if not torrent:
                logger.debug('Attempting to retrieve {} from HTTP caching service'
                             .format(filename))
                urls = [
                    'https://watercache.libertycorp.org/get/{}/{}',
                    'https://itorrents.org/torrent/{}.torrent?title={}',
                    'https://firecache.libertycorp.org/get/{}/{}',
                    'http://fcache63sakpihd44kxdduy6kgpdhgejgp323wci435zwy6kiylcnfad.onion/get/{}/{}'
                    ]
                for url in urls:
                    torrent = fetch.http(url.format(checksum, filename))
                    if torrent:
                        break
        return torrent