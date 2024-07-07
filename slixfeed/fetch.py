#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

FIXME

1) feed_mode_scan doesn't find feed for https://www.blender.org/
   even though it should be according to the pathnames dictionary.

TODO

1) Support Gemini and Gopher.

2) Check also for HTML, not only feed.bozo.

3) Add "if utility.is_feed(url, feed)" to view_entry and view_feed

4) Replace sqlite.remove_nonexistent_entries by sqlite.check_entry_exist
   Same check, just reverse.

5) Support protocol Gopher
   See project /michael-lazar/pygopherd
   See project /gopherball/gb

6) Support ActivityPub @person@domain (see Tip Of The Day).
    
7) See project /offpunk/offblocklist.py

NOTE

1) You might not want to utilize aiohttp, because you
   no more scan as many feeds as possible all at once
   due to CPU spike.
   Consider https://pythonhosted.org/feedparser/http-useragent.html

"""

import aiofiles
from aiohttp import ClientError, ClientSession, ClientTimeout
from asyncio import TimeoutError
# from asyncio.exceptions import IncompleteReadError
# from http.client import IncompleteRead
# from lxml import html
# from xml.etree.ElementTree import ElementTree, ParseError
import requests
import slixfeed.config as config
from slixfeed.log import Logger
# import urllib.request
# from urllib.error import HTTPError

logger = Logger(__name__)

try:
    from magnet2torrent import Magnet2Torrent, FailedToFetchException
except:
    logger.info(
        "Package magnet2torrent was not found.\n"
        "BitTorrent is disabled.")

# class Dat:
# async def dat():

# class Ftp:
# async def ftp():

# class Gemini:
# async def gemini():

# class Gopher:
# async def gopher():

# class Ipfs:
# async def ipfs():


class Http:


    # def fetch_media(url, pathname):
    #     try:
    #         urllib.request.urlretrieve(url, pathname)
    #         status = 1
    #     except HTTPError as e:
    #         logger.error(e)
    #         status = 0
    #     return status


    async def fetch_headers(url):
        network_settings = config.get_values('settings.toml', 'network')
        user_agent = (network_settings['user_agent'] or 'Slixfeed/0.1')
        headers = {'User-Agent': user_agent}
        proxy = (network_settings['http_proxy'] or None)
        timeout = ClientTimeout(total=10)
        async with ClientSession(headers=headers) as session:
            async with session.get(url, proxy=proxy,
                                   # proxy_auth=(proxy_username, proxy_password),
                                   timeout=timeout
                                   ) as response:
                headers = response.headers
                return headers
                # print("Headers for URL:", url)
                # for header_name, header_value in headers.items():
                #     print(f"{header_name}: {header_value}")


    # TODO Write file to disk. Consider aiofiles
    async def fetch_media(url, pathname):
        """
        Download media content of given URL.

        Parameters
        ----------
        url : str
            URL.
        pathname : list
            Pathname (including filename) to save content to.

        Returns
        -------
        msg: list or str
            Document or error message.
        """
        network_settings = config.get_values('settings.toml', 'network')
        user_agent = (network_settings['user_agent'] or 'Slixfeed/0.1')
        headers = {'User-Agent': user_agent}
        proxy = (network_settings['http_proxy'] or None)
        timeout = ClientTimeout(total=10)
        async with ClientSession(headers=headers) as session:
        # async with ClientSession(trust_env=True) as session:
            try:
                async with session.get(url, proxy=proxy,
                                       # proxy_auth=(proxy_username, proxy_password),
                                       timeout=timeout
                                       ) as response:
                    status = response.status
                    if status in (200, 201):
                        f = await aiofiles.open(pathname, mode='wb')
                        await f.write(await response.read())
                        await f.close()
                        try:
                            result = {'charset': response.charset,
                                      'content_length': response.content_length,
                                      'content_type': response.content_type,
                                      'error': False,
                                      'message': None,
                                      'original_url': url,
                                      'status_code': status,
                                      'response_url': response.url}
                        except:
                            result = {'error': True,
                                      'message': 'Could not get document.',
                                      'original_url': url,
                                      'status_code': status,
                                      'response_url': response.url}
                    else:
                        result = {'error': True,
                                  'message': 'HTTP Error:' + str(status),
                                  'original_url': url,
                                  'status_code': status,
                                  'response_url': response.url}
            except ClientError as e:
                result = {'error': True,
                          'message': 'Error:' + str(e) if e else 'ClientError',
                          'original_url': url,
                          'status_code': None}
            except TimeoutError as e:
                result = {'error': True,
                          'message': 'Timeout:' + str(e) if e else 'TimeoutError',
                          'original_url': url,
                          'status_code': None}
            except Exception as e:
                logger.error(e)
                result = {'error': True,
                          'message': 'Error:' + str(e) if e else 'Error',
                          'original_url': url,
                          'status_code': None}
        return result


    def http_response(url):
        """
        Download response headers.
    
        Parameters
        ----------
        url : str
            URL.
    
        Returns
        -------
        response: requests.models.Response
            HTTP Header Response.
    
        Result would contain these:
            response.encoding
            response.headers
            response.history
            response.reason
            response.status_code
            response.url
        """
        user_agent = (
            config.get_value(
                "settings", "Network", "user_agent")
            ) or 'Slixfeed/0.1'
        headers = {
            "User-Agent": user_agent
        }
        try:
            # Do not use HEAD request because it appears that too many sites would
            # deny it.
            # response = requests.head(url, headers=headers, allow_redirects=True)
            response = requests.get(url, headers=headers, allow_redirects=True)
        except Exception as e:
            logger.warning('Error in HTTP response')
            logger.error(e)
            response = None
        return response


async def http(url):
    """
    Download content of given URL.

    Parameters
    ----------
    url : list
        URL.

    Returns
    -------
    msg: list or str
        Document or error message.
    """
    network_settings = config.get_values('settings.toml', 'network')
    user_agent = (network_settings['user_agent'] or 'Slixfeed/0.1')
    headers = {'User-Agent': user_agent}
    proxy = (network_settings['http_proxy'] or None)
    timeout = ClientTimeout(total=10)
    async with ClientSession(headers=headers) as session:
    # async with ClientSession(trust_env=True) as session:
        try:
            async with session.get(url, proxy=proxy,
                                   # proxy_auth=(proxy_username, proxy_password),
                                   timeout=timeout
                                   ) as response:
                status = response.status
                if status == 200:
                    try:
                        document = await response.text()
                        result = {'charset': response.charset,
                                  'content': document,
                                  'content_length': response.content_length,
                                  'content_type': response.content_type,
                                  'error': False,
                                  'message': None,
                                  'original_url': url,
                                  'status_code': status,
                                  'response_url': response.url}
                    except:
                        result = {'error': True,
                                  'message': 'Could not get document.',
                                  'original_url': url,
                                  'status_code': status,
                                  'response_url': response.url}
                else:
                    result = {'error': True,
                              'message': 'HTTP Error:' + str(status),
                              'original_url': url,
                              'status_code': status,
                              'response_url': response.url}
        except ClientError as e:
            result = {'error': True,
                      'message': 'Error:' + str(e) if e else 'ClientError',
                      'original_url': url,
                      'status_code': None}
        except TimeoutError as e:
            result = {'error': True,
                      'message': 'Timeout:' + str(e) if e else 'TimeoutError',
                      'original_url': url,
                      'status_code': None}
        except Exception as e:
            logger.error(e)
            result = {'error': True,
                      'message': 'Error:' + str(e) if e else 'Error',
                      'original_url': url,
                      'status_code': None}
    return result


async def magnet(link):
    m2t = Magnet2Torrent(link)
    try:
        filename, torrent_data = await m2t.retrieve_torrent()
    except FailedToFetchException:
        logger.debug("Failed")
