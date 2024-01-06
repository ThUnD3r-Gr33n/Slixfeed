#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

TODO

1) ActivityPub URL revealer activitypub_to_http.

"""

from email.utils import parseaddr
import random
import slixfeed.config as config
from urllib.parse import (
    parse_qs,
    urlencode,
    urljoin,
    # urlparse,
    urlsplit,
    urlunsplit
    )


# NOTE hostname and protocol are listed as one in file
# proxies.yaml. Perhaps a better practice would be to have
# them separated. File proxies.yaml will remainas is in order
# to be coordinated with the dataset of project LibRedirect.
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
    parted_url = urlsplit(url)
    protocol = parted_url.scheme
    hostname = parted_url.netloc
    hostname = hostname.replace("www.","")
    pathname = parted_url.path
    queries = parted_url.query
    fragment = parted_url.fragment
    proxies = config.get_list("proxies.yaml", "proxies")
    for proxy in proxies:
        proxy = proxies[proxy]
        if hostname in proxy["hostname"] and url_type in proxy["type"]:
            select_proxy = random.choice(proxy["clearnet"])
            parted_proxy = urlsplit(select_proxy)
            protocol_new = parted_proxy.scheme
            hostname_new = parted_proxy.netloc
            url = urlunsplit([
                protocol_new,
                hostname_new,
                pathname,
                queries,
                fragment
                ])
            return url


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
    parted_url = urlsplit(url)
    protocol = parted_url.scheme
    hostname = parted_url.netloc
    pathname = parted_url.path
    queries = parse_qs(parted_url.query)
    fragment = parted_url.fragment
    trackers = config.get_list("queries.yaml", "trackers")
    for tracker in trackers:
        if tracker in queries: del queries[tracker]
    queries_new = urlencode(queries, doseq=True)
    url = urlunsplit([
        protocol,
        hostname,
        pathname,
        queries_new,
        fragment
        ])
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
    new_url = urlunsplit([
        "http",
        par_url.netloc,
        par_url.path,
        par_url.query,
        par_url.fragment
        ])
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
    if link.startswith("www."):
        return "http://" + link
    parted_link = urlsplit(link)
    parted_feed = urlsplit(source)
    if parted_link.scheme == "magnet" and parted_link.query:
        return link
    if parted_link.scheme and parted_link.netloc:
        return link
    if link.startswith("//"):
        if parted_link.netloc and parted_link.path:
            new_link = urlunsplit([
                parted_feed.scheme,
                parted_link.netloc,
                parted_link.path,
                parted_link.query,
                parted_link.fragment
                ])
    elif link.startswith("/"):
        new_link = urlunsplit([
            parted_feed.scheme,
            parted_feed.netloc,
            parted_link.path,
            parted_link.query,
            parted_link.fragment
            ])
    elif link.startswith("../"):
        pathlink = parted_link.path.split("/")
        pathfeed = parted_feed.path.split("/")
        for i in pathlink:
            if i == "..":
                if pathlink.index("..") == 0:
                    pathfeed.pop()
                else:
                    break
        while pathlink.count(".."):
            if pathlink.index("..") == 0:
                pathlink.remove("..")
            else:
                break
        pathlink = "/".join(pathlink)
        pathfeed.extend([pathlink])
        new_link = urlunsplit([
            parted_feed.scheme,
            parted_feed.netloc,
            "/".join(pathfeed),
            parted_link.query,
            parted_link.fragment
            ])
    else:
        pathlink = parted_link.path.split("/")
        pathfeed = parted_feed.path.split("/")
        if link.startswith("./"):
            pathlink.remove(".")
        if not source.endswith("/"):
            pathfeed.pop()
        pathlink = "/".join(pathlink)
        pathfeed.extend([pathlink])
        new_link = urlunsplit([
            parted_feed.scheme,
            parted_feed.netloc,
            "/".join(pathfeed),
            parted_link.query,
            parted_link.fragment
            ])
    return new_link


"""
TODO
Feed https://www.ocaml.org/feed.xml
Link %20https://frama-c.com/fc-versions/cobalt.html%20

FIXME
Feed https://cyber.dabamos.de/blog/feed.rss
Link https://cyber.dabamos.de/blog/#article-2022-07-15
"""
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
    if link.startswith("www."):
        new_link = "http://" + link
    elif link.startswith("%20") and link.endswith("%20"):
        old_link = link.split("%20")
        del old_link[0]
        old_link.pop()
        new_link = "".join(old_link)
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
    parted_url = urlsplit(url)
    protocol = parted_url.scheme
    hostname = parted_url.netloc
    pathname = parted_url.path
    queries = parted_url.query
    fragment = parted_url.fragment
    while "//" in pathname:
        pathname = pathname.replace("//", "/")
    url = urlunsplit([
        protocol,
        hostname,
        pathname,
        queries,
        fragment
        ])
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
