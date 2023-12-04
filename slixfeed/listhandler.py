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

from sqlitehandler import get_settings_value


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


async def is_listed(db_file, key, string):
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
    list = await get_settings_value(
        db_file,
        key
        )
    if list:
        list = list.split(",")
        for i in list:
            if not i or len(i) < 2:
                continue
            if i in string.lower():
                # print(">>> ACTIVATE", i)
                # return 1
                return i
    else:
        return None

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