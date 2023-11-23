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

import sqlitehandler

async def set_filter(newwords, keywords):
    """
    Append new keywords to filter.

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

async def is_listed(db_file, type, string):
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
    filter_type = "filter-" + type
    list = await sqlitehandler.get_settings_value(
        db_file,
        filter_type
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
                    blacklist = await sqlitehandler.get_settings_value(
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