#!/usr/bin/env python

from distutils.core import setup

setup(
    name='slixfeed',
    version='1.0',
    description='rss through xmpp bot',
    install_require=[
        'aiohttp',
        'slixmpp',
        'eliot',
        'feedparser'
    ]
)
