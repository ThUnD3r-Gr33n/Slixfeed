#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

FIXME

1) Do not handle base64
   https://www.lilithsaintcrow.com/2024/02/love-anonymous/
   data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAABaAAAAeAAQAAAAAQ6M16AAAAAnRSTlMAAHaTzTgAAAFmSURBVBgZ7cEBAQAAAIKg/q92SMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADgWE3LAAGyZmPPAAAAAElFTkSuQmCC
   https://www.lilithsaintcrow.com/2024/02/love-anonymous//image/png;base64,iVBORw0KGgoAAAANSUhEUgAABaAAAAeAAQAAAAAQ6M16AAAAAnRSTlMAAHaTzTgAAAFmSURBVBgZ7cEBAQAAAIKg/q92SMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADgWE3LAAGyZmPPAAAAAElFTkSuQmCC

TODO

1) ActivityPub URL revealer activitypub_to_http.

2) SQLite preference "instance" for preferred instances.

"""

from email.utils import parseaddr
import logging
import os
import random
import slixfeed.config as config
import slixfeed.fetch as fetch
from urllib.parse import (
    parse_qs,
    urlencode,
    urljoin,
    # urlparse,
    urlsplit,
    urlunsplit
    )


# NOTE
# hostname and protocol are listed as one in file proxies.toml.
# Perhaps a better practice would be to have them separated.

# NOTE
# File proxies.toml will remain as it is, in order to be
# coordinated with the dataset of project LibRedirect, even
# though rule-sets might be adopted (see )Privacy Redirect).

def get_hostname(url):
    parted_url = urlsplit(url)
    return parted_url.netloc


def replace_hostname(url, url_type):
    """
    Replace hostname.

    Parameters
    ----------
    url : str
        URL.
    url_type : str
        "feed" or "link".

    Returns
    -------
    url : str
        URL.
    """
    url_new = None
    parted_url = urlsplit(url)
    # protocol = parted_url.scheme
    hostname = parted_url.netloc
    hostname = hostname.replace('www.','')
    pathname = parted_url.path
    queries = parted_url.query
    fragment = parted_url.fragment
    proxies = config.open_config_file('proxies.toml')['proxies']
    for proxy_name in proxies:
        proxy = proxies[proxy_name]
        if hostname in proxy['hostname'] and url_type in proxy['type']:
            while not url_new:
                proxy_type = 'clearnet'
                proxy_list = proxy[proxy_type]
                if len(proxy_list):
                    # proxy_list = proxies[proxy_name][proxy_type]
                    proxy_url = random.choice(proxy_list)
                    parted_proxy_url = urlsplit(proxy_url)
                    protocol_new = parted_proxy_url.scheme
                    hostname_new = parted_proxy_url.netloc
                    url_new = urlunsplit([protocol_new, hostname_new,
                                          pathname, queries, fragment])
                    response = fetch.http_response(url_new)
                    if (response and
                        response.status_code == 200 and
                        response.reason == 'OK' and
                        url_new.startswith(proxy_url)):
                        break
                    else:
                        config_dir = config.get_default_config_directory()
                        proxies_obsolete_file = config_dir + '/proxies_obsolete.toml'
                        proxies_file = config_dir + '/proxies.toml'
                        if not os.path.isfile(proxies_obsolete_file):
                            config.create_skeleton(proxies_file)
                        config.backup_obsolete(proxies_obsolete_file,
                                               proxy_name, proxy_type,
                                               proxy_url)
                        config.update_proxies(proxies_file, proxy_name,
                                              proxy_type, proxy_url)
                        url_new = None
                else:
                    logging.warning(
                        "No proxy URLs for {}."
                        "Update proxies.toml".format(proxy_name))
                    url_new = url
                    break
    return url_new


def remove_tracking_parameters(url):
    """
    Remove queries with tracking parameters.

    Parameters
    ----------
    url : str
        URL.

    Returns
    -------
    url : str
        URL.
    """
    if url.startswith('data:') and ';base64,' in url:
        return url
    parted_url = urlsplit(url)
    protocol = parted_url.scheme
    hostname = parted_url.netloc
    pathname = parted_url.path
    queries = parse_qs(parted_url.query)
    fragment = parted_url.fragment
    trackers = config.open_config_file('queries.toml')['trackers']
    for tracker in trackers:
        if tracker in queries: del queries[tracker]
    queries_new = urlencode(queries, doseq=True)
    url = urlunsplit([protocol, hostname, pathname, queries_new, fragment])
    return url


def feed_to_http(url):
    """
    Replace scheme FEED by HTTP.

    Parameters
    ----------
    url : str
        URL.

    Returns
    -------
    new_url : str
        URL.
    """
    par_url = urlsplit(url)
    new_url = urlunsplit(['http', par_url.netloc, par_url.path, par_url.query,
                          par_url.fragment])
    return new_url


def check_xmpp_uri(uri):
    """
    Check validity of XMPP URI.

    Parameters
    ----------
    uri : str
        URI.

    Returns
    -------
    jid : str
        JID or None.
    """
    jid = urlsplit(uri).path
    if parseaddr(jid)[1] != jid:
        jid = False
    return jid


# NOTE Read the documentation
# https://docs.python.org/3/library/urllib.parse.html#urllib.parse.urljoin
def complete_url(source, link):
    """
    Check if URL is pathname and complete it into URL.

    Parameters
    ----------
    source : str
        Feed URL.
    link : str
        Link URL or pathname.

    Returns
    -------
    str
        URL.
    """
    if link.startswith('data:') and ';base64,' in link:
        return link
    if link.startswith('www.'):
        return 'http://' + link
    parted_link = urlsplit(link)
    parted_feed = urlsplit(source)
    if parted_link.scheme == 'magnet' and parted_link.query:
        return link
    if parted_link.scheme and parted_link.netloc:
        return link
    if link.startswith('//'):
        if parted_link.netloc and parted_link.path:
            new_link = urlunsplit([parted_feed.scheme, parted_link.netloc,
                                   parted_link.path, parted_link.query,
                                   parted_link.fragment])
    elif link.startswith('/'):
        new_link = urlunsplit([parted_feed.scheme, parted_feed.netloc,
                               parted_link.path, parted_link.query,
                               parted_link.fragment])
    elif link.startswith('../'):
        pathlink = parted_link.path.split('/')
        pathfeed = parted_feed.path.split('/')
        for i in pathlink:
            if i == '..':
                if pathlink.index('..') == 0:
                    pathfeed.pop()
                else:
                    break
        while pathlink.count('..'):
            if pathlink.index('..') == 0:
                pathlink.remove('..')
            else:
                break
        pathlink = '/'.join(pathlink)
        pathfeed.extend([pathlink])
        new_link = urlunsplit([parted_feed.scheme, parted_feed.netloc,
                               '/'.join(pathfeed), parted_link.query,
                               parted_link.fragment])
    else:
        pathlink = parted_link.path.split('/')
        pathfeed = parted_feed.path.split('/')
        if link.startswith('./'):
            pathlink.remove('.')
        if not source.endswith('/'):
            pathfeed.pop()
        pathlink = '/'.join(pathlink)
        pathfeed.extend([pathlink])
        new_link = urlunsplit([parted_feed.scheme, parted_feed.netloc,
                               '/'.join(pathfeed), parted_link.query,
                               parted_link.fragment])
    return new_link



# TODO

# Feed https://www.ocaml.org/feed.xml
# Link %20https://frama-c.com/fc-versions/cobalt.html%20

# FIXME

# Feed https://cyber.dabamos.de/blog/feed.rss
# Link https://cyber.dabamos.de/blog/#article-2022-07-15

def join_url(source, link):
    """
    Join base URL with given pathname.

    Parameters
    ----------
    source : str
        Feed URL.
    link : str
        Link URL or pathname.

    Returns
    -------
    str
        URL.
    """
    if link.startswith('data:') and ';base64,' in link:
        return link
    if link.startswith('www.'):
        new_link = 'http://' + link
    elif link.startswith('%20') and link.endswith('%20'):
        old_link = link.split('%20')
        del old_link[0]
        old_link.pop()
        new_link = ''.join(old_link)
    else:
        new_link = urljoin(source, link)
    return new_link


def trim_url(url):
    """
    Check URL pathname for double slash.

    Parameters
    ----------
    url : str
        URL.

    Returns
    -------
    url : str
        URL.
    """
    if url.startswith('data:') and ';base64,' in url:
        return url
    parted_url = urlsplit(url)
    protocol = parted_url.scheme
    hostname = parted_url.netloc
    pathname = parted_url.path
    queries = parted_url.query
    fragment = parted_url.fragment
    while '//' in pathname:
        pathname = pathname.replace('//', '/')
    url = urlunsplit([protocol, hostname, pathname, queries, fragment])
    return url


def activitypub_to_http(namespace):
    """
    Replace ActivityPub namespace by HTTP.

    Parameters
    ----------
    namespace : str
        Namespace.

    Returns
    -------
    new_url : str
        URL.
    """
