#!/usr/bin/env python

from distutils.core import setup

setup(
    name='Slixfeed',
    version='1.0',
    description='RSS news bot for XMPP',
    long_description='Slixfeed is a news aggregator bot for online news feeds. This program is primarily designed for XMPP',
    author='Schimon Jehudah Zakai Zockaim Zachary',
    author_email='sjehuda@yandex.com',
    url='https://gitgud.io/sjehuda/slixfeed',
    license='MIT',
    platforms=['any'],
    install_require=[
        'aiohttp',
        'bs4',
        'feedparser',
        'lxml',
        'slixmpp'
    ],
    classifiers=[
        'Framework :: slixmpp',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.10',
        'Topic :: Communications :: Chat',
        'Topic :: Internet :: Extensible Messaging and Presence Protocol (XMPP)',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content :: News/Diary',
        'Topic :: Internet :: Instant Messaging',
        'Topic :: Internet :: XMPP',
        'Topic :: Office/Business :: News/Diary',
    ],
    keywords=[
        'jabber',
        'xmpp',
        'bot',
        'chat',
        'im',
        'news',
        'atom',
        'rdf',
        'rss',
        'syndication'
    ],
)
