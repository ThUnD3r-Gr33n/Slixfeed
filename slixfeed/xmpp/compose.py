#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TODO Port functions insert_feed, remove_feed, get_entry_unread
"""

import slixfeed.xmpp.bookmark as bookmark
from slixfeed.url import remove_tracking_parameters, replace_hostname


def list_search_results(query, results):
    results_list = (
        "Search results for '{}':\n\n```"
        ).format(query)
    counter = 0
    for result in results:
        counter += 1
        results_list += (
            "\n{}\n{}\n"
            ).format(str(result[0]), str(result[1]))
    if counter:
        return results_list + "```\nTotal of {} results".format(counter)
    else:
        return "No results were found for: {}".format(query)


def list_feeds_by_query(query, results):
    results_list = (
        "Feeds containing '{}':\n\n```"
        ).format(query)
    counter = 0
    for result in results:
        counter += 1
        results_list += (
            "\nName  : {}"
            "\nURL   : {}"
            "\nIndex : {}"
            "\nMode  : {}"
            "\n"
            ).format(str(result[0]), str(result[1]),
                     str(result[2]), str(result[3]))
    if counter:
        return results_list + "\n```\nTotal of {} feeds".format(counter)
    else:
        return "No feeds were found for: {}".format(query)


def list_statistics(values):
    """
    Return table statistics.

    Parameters
    ----------
    db_file : str
        Path to database file.

    Returns
    -------
    msg : str
        Statistics as message.
    """
    msg = (
        "```"
        "\nSTATISTICS\n"
        "News items   : {}/{}\n"
        "News sources : {}/{}\n"
        "\nOPTIONS\n"
        "Items to archive : {}\n"
        "Update interval  : {}\n"
        "Items per update : {}\n"
        "Operation status : {}\n"
        "```"
        ).format(values[0], values[1], values[2], values[3],
                 values[4], values[5], values[6], values[7])
    return msg


async def list_last_entries(results, num):
    titles_list = "Recent {} titles:\n\n```".format(num)
    counter = 0
    for result in results:
        counter += 1
        titles_list += (
            "\n{}\n{}\n"
            ).format(str(result[0]), str(result[1]))
    if counter:
        titles_list += "```\n"
        return titles_list
    else:
        return "There are no news at the moment."


async def list_feeds(results):
    feeds_list = "\nList of subscriptions:\n\n```\n"
    counter = 0
    for result in results:
        counter += 1
        feeds_list += (
            "Name    : {}\n"
            "Address : {}\n"
            "Updated : {}\n"
            "Status  : {}\n"
            "ID      : {}\n"
            "\n"
            ).format(str(result[0]), str(result[1]), str(result[2]),
                     str(result[3]), str(result[4]))
    if counter:
        return feeds_list + (
            "```\nTotal of {} subscriptions.\n"
            ).format(counter)
    else:
        msg = (
            "List of subscriptions is empty.\n"
            "To add feed, send a URL\n"
            "Try these:\n"
            # TODO Pick random from featured/recommended
            "https://reclaimthenet.org/feed/"
            )
        return msg


async def list_bookmarks(self):
    conferences = bookmark.get(self)
    groupchat_list = "\nList of groupchats:\n\n```\n"
    counter = 0
    for conference in conferences:
        counter += 1
        groupchat_list += (
            "{}\n"
            "\n"
            ).format(
                conference["jid"]
                )
    groupchat_list += (
        "```\nTotal of {} groupchats.\n"
        ).format(counter)
    return groupchat_list