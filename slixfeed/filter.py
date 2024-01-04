#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

TODO

1) Website-specific filter (i.e. audiobookbay).

2) Exclude websites from filtering (e.g. metapedia).

3) Filter phrases:
    Refer to sqlitehandler.search_entries for implementation.
    It is expected to be more complex than function search_entries.

"""

import slixfeed.config as config
import slixfeed.sqlite as sqlite


async def add_to_list(newwords, keywords):
    """
    Append new keywords to list.

    Parameters
    ----------
    newwords : str
        List of new keywords.
    keywords : str
        List of current keywords.

    Returns
    -------
    val : str
        List of current keywords and new keywords.
    """
    if isinstance(keywords, str) or keywords is None:
        try:
            keywords = keywords.split(",")
        except:
            keywords = []
    newwords = newwords.lower().split(",")
    for word in newwords:
        word = word.strip()
        if len(word) and word not in keywords:
            keywords.extend([word])
    keywords.sort()
    val = ",".join(keywords)
    return val


async def remove_from_list(newwords, keywords):
    """
    Remove given keywords from list.

    Parameters
    ----------
    newwords : str
        List of new keywords.
    keywords : str
        List of current keywords.

    Returns
    -------
    val : str
        List of new keywords.
    """
    if isinstance(keywords, str) or keywords is None:
        try:
            keywords = keywords.split(",")
        except:
            keywords = []
    newwords = newwords.lower().split(",")
    for word in newwords:
        word = word.strip()
        if len(word) and word in keywords:
            keywords.remove(word)
    keywords.sort()
    val = ",".join(keywords)
    return val


async def is_include_keyword(db_file, key, string):
    """
    Check keyword match.

    Parameters
    ----------
    db_file : str
        Path to database file.
    type : str
        "allow" or "deny".
    string : str
        String.

    Returns
    -------
    Matched keyword or None.

    """
# async def reject(db_file, string):
# async def is_blacklisted(db_file, string):
    keywords = (await sqlite.get_filters_value(db_file, key)) or ''
    keywords = keywords.split(",")
    keywords = keywords + (config.get_list("lists.yaml", key))
    for keyword in keywords:
        if not keyword or len(keyword) < 2:
            continue
        if keyword in string.lower():
            # print(">>> ACTIVATE", i)
            # return 1
            return keyword

"""

This code was tested at module datahandler

reject = 0
blacklist = await get_settings_value(
    db_file,
    "filter-deny"
    )
# print(">>> blacklist:")
# print(blacklist)
# breakpoint()
if blacklist:
    blacklist = blacklist.split(",")
    # print(">>> blacklist.split")
    # print(blacklist)
    # breakpoint()
    for i in blacklist:
        # print(">>> length", len(i))
        # breakpoint()
        # if len(i):
        if not i or len(i) < 2:
            print(">>> continue due to length", len(i))
            # breakpoint()
            continue
        # print(title)
        # print(">>> blacklisted word:", i)
        # breakpoint()
        test = (title + " " + summary + " " + link)
        if i in test.lower():
            reject = 1
            break
        
if reject:
    print("rejected:",title)
    entry = (title, '', link, source, date, 1);

"""