#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from asyncio.exceptions import IncompleteReadError
from bs4 import BeautifulSoup
from http.client import IncompleteRead
from feedparser import parse
import slixfeed.config as config
import slixfeed.crawl as crawl
from slixfeed.datetime import now, rfc2822_to_iso8601
import slixfeed.fetch as fetch
import slixfeed.sqlite as sqlite
import slixfeed.read as read
import slixfeed.task as task
from slixfeed.url import complete_url, join_url, trim_url
from urllib import error
from urllib.parse import urlsplit


async def add_feed(db_file, url):
    while True:
        exist = await sqlite.is_feed_exist(db_file, url)
        if not exist:
            result = await fetch.download_feed(url)
            document = result[0]
            status = result[1]
            if document:
                feed = parse(document)
                # if read.is_feed(url, feed):
                if read.is_feed(feed):
                    try:
                        title = feed["feed"]["title"]
                    except:
                        title = urlsplit(url).netloc
                    await sqlite.insert_feed(
                        db_file, url, title, status)
                    await organize_items(
                        db_file, [url])
                    old = (
                        await sqlite.get_settings_value(
                            db_file, "old")
                        ) or (
                        config.get_value_default(
                            "settings", "Settings", "old")
                        )
                    if not old:
                        await sqlite.mark_source_as_read(
                            db_file, url)
                    response = (
                        "> {}\nNews source {} has been "
                        "added to subscription list."
                        ).format(url, title)
                    break
                else:
                    result = await crawl.probe_page(
                        url, document)
                    # TODO Check length and for a write a
                    # unified message for a set of feeds.
                    # Use logging if you so choose to
                    # distinct the methods
                    if isinstance(result, list):
                        url = result[0]
                    elif isinstance(result, str):
                        response = result
                        break
            else:
                response = (
                    "> {}\nFailed to load URL.  Reason: {}"
                    ).format(url, status)
                break
        else:
            ix = exist[0]
            name = exist[1]
            response = (
                "> {}\nNews source \"{}\" is already "
                "listed in the subscription list at "
                "index {}".format(url, name, ix)
                )
            break
    return response


async def view_feed(url):
    while True:
        result = await fetch.download_feed(url)
        document = result[0]
        status = result[1]
        if document:
            feed = parse(document)
            # if read.is_feed(url, feed):
            if read.is_feed(feed):
                try:
                    title = feed["feed"]["title"]
                except:
                    title = urlsplit(url).netloc
                entries = feed.entries
                response = "Preview of {}:\n\n```\n".format(title)
                counter = 0
                for entry in entries:
                    counter += 1
                    if entry.has_key("title"):
                        title = entry.title
                    else:
                        title = "*** No title ***"
                    if entry.has_key("link"):
                        # link = complete_url(source, entry.link)
                        link = join_url(url, entry.link)
                        link = trim_url(link)
                    else:
                        link = "*** No link ***"
                    if entry.has_key("published"):
                        date = entry.published
                        date = rfc2822_to_iso8601(date)
                    elif entry.has_key("updated"):
                        date = entry.updated
                        date = rfc2822_to_iso8601(date)
                    else:
                        date = "*** No date ***"
                    response += (
                        "Title : {}\n"
                        "Date  : {}\n"
                        "Link  : {}\n"
                        "Count : {}\n"
                        "\n"
                        ).format(title, date, link, counter)
                    if counter > 4:
                        break
                response += (
                    "```\nSource: {}"
                    ).format(url)
                break
            else:
                result = await crawl.probe_page(
                    url, document)
                # TODO Check length and for a write a
                # unified message for a set of feeds.
                # Use logging if you so choose to
                # distinct the methods
                if isinstance(result, list):
                    url = result[0]
                elif isinstance(result, str):
                    response = result
                    break
        else:
            response = (
                "> {}\nFailed to load URL.  Reason: {}"
                ).format(url, status)
            break
    return response


async def view_entry(url, num):
    while True:
        result = await fetch.download_feed(url)
        document = result[0]
        status = result[1]
        if document:
            feed = parse(document)
            # if read.is_feed(url, feed):
            if read.is_feed(feed):
                try:
                    title = feed["feed"]["title"]
                except:
                    title = urlsplit(url).netloc
                entries = feed.entries
                num = int(num) - 1
                entry = entries[num]
                response = "Preview of {}:\n\n```\n".format(title)
                if entry.has_key("title"):
                    title = entry.title
                else:
                    title = "*** No title ***"
                if entry.has_key("published"):
                    date = entry.published
                    date = rfc2822_to_iso8601(date)
                elif entry.has_key("updated"):
                    date = entry.updated
                    date = rfc2822_to_iso8601(date)
                else:
                    date = "*** No date ***"
                if entry.has_key("summary"):
                    summary = entry.summary
                    # Remove HTML tags
                    summary = BeautifulSoup(summary, "lxml").text
                    # TODO Limit text length
                    summary = summary.replace("\n\n\n", "\n\n")
                else:
                    summary = "*** No summary ***"
                if entry.has_key("link"):
                    # link = complete_url(source, entry.link)
                    link = join_url(url, entry.link)
                    link = trim_url(link)
                else:
                    link = "*** No link ***"
                response = (
                    "{}\n"
                    "\n"
                    # "> {}\n"
                    "{}\n"
                    "\n"
                    "{}\n"
                    "\n"
                    ).format(title, summary, link)
                break
            else:
                result = await crawl.probe_page(
                    url, document)
                # TODO Check length and for a write a
                # unified message for a set of feeds.
                # Use logging if you so choose to
                # distinct the methods
                if isinstance(result, list):
                    url = result[0]
                elif isinstance(result, str):
                    response = result
                    break
        else:
            response = (
                "> {}\nFailed to load URL.  Reason: {}"
                ).format(url, status)
            break
    return response


# NOTE Why (if res[0]) and (if res[1] == 200)?
async def organize_items(db_file, urls):
    """
    Check feeds for new entries.

    Parameters
    ----------
    db_file : str
        Path to database file.
    url : str, optional
        URL. The default is None.
    """
    for url in urls:
        # print(os.path.basename(db_file), url[0])
        source = url[0]
        res = await fetch.download_feed(source)
        # TypeError: 'NoneType' object is not subscriptable
        if res is None:
            # Skip to next feed
            # urls.next()
            # next(urls)
            continue
        await sqlite.update_source_status(
            db_file, res[1], source)
        if res[0]:
            try:
                feed = parse(res[0])
                if feed.bozo:
                    # bozo = (
                    #     "WARNING: Bozo detected for feed: {}\n"
                    #     "For more information, visit "
                    #     "https://pythonhosted.org/feedparser/bozo.html"
                    #     ).format(source)
                    # print(bozo)
                    valid = 0
                else:
                    valid = 1
                await sqlite.update_source_validity(
                    db_file, source, valid)
            except (
                    IncompleteReadError,
                    IncompleteRead,
                    error.URLError
                    ) as e:
                # print(e)
                # TODO Print error to log
                None
                # NOTE I don't think there should be "return"
                # because then we might stop scanning next URLs
                # return
        # TODO Place these couple of lines back down
        # NOTE Need to correct the SQL statement to do so
        # NOT SURE WHETHER I MEANT THE LINES ABOVE OR BELOW
        if res[1] == 200:
        # NOT SURE WHETHER I MEANT THE LINES ABOVE OR BELOW
        # TODO Place these couple of lines back down
        # NOTE Need to correct the SQL statement to do so
            entries = feed.entries
            # length = len(entries)
            # await remove_entry(db_file, source, length)
            await remove_nonexistent_entries(
                db_file, feed, source)
            # new_entry = 0
            for entry in entries:
                # TODO Pass date too for comparion check
                if entry.has_key("published"):
                    date = entry.published
                    date = rfc2822_to_iso8601(date)
                elif entry.has_key("updated"):
                    date = entry.updated
                    date = rfc2822_to_iso8601(date)
                else:
                    # TODO Just set date = "*** No date ***"
                    # date = await datetime.now().isoformat()
                    date = now()
                    # NOTE Would seconds result in better database performance
                    # date = datetime.datetime(date)
                    # date = (date-datetime.datetime(1970,1,1)).total_seconds()
                if entry.has_key("title"):
                    title = entry.title
                    # title = "{}: *{}*".format(feed["feed"]["title"], entry.title)
                else:
                    title = date
                    # title = feed["feed"]["title"]
                if entry.has_key("link"):
                    # link = complete_url(source, entry.link)
                    link = join_url(source, entry.link)
                    link = trim_url(link)
                else:
                    link = source
                if entry.has_key("id"):
                    eid = entry.id
                else:
                    eid = link
                exist = await sqlite.check_entry_exist(
                    db_file, source, eid=eid,
                    title=title, link=link, date=date)
                if not exist:
                    print(url)
                    # new_entry = new_entry + 1
                    # TODO Enhance summary
                    if entry.has_key("summary"):
                        summary = entry.summary
                        # # Remove HTML tags
                        # summary = BeautifulSoup(summary, "lxml").text
                        # # TODO Limit text length
                        # summary = summary.replace("\n\n\n", "\n\n")
                        # summary = summary[:300] + " […]‍⃨"
                        # summary = summary.strip().split('\n')
                        # summary = ["> " + line for line in summary]
                        # summary = "\n".join(summary)
                    else:
                        summary = "> *** No summary ***"
                    read_status = 0
                    pathname = urlsplit(link).path
                    string = ("{} {} {}"
                              ).format(
                                  title, summary, pathname
                                  )
                    allow_list = await config.is_include_keyword(
                        db_file, "filter-allow", string)
                    if not allow_list:
                        reject_list = await config.is_include_keyword(
                            db_file, "filter-deny", string)
                        if reject_list:
                            # print(">>> REJECTED", title)
                            summary = (
                                "REJECTED {}".format(
                                    reject_list.upper()
                                    )
                                )
                            # summary = ""
                            read_status = 1
                    entry = (
                        title, link, eid, source, date, read_status)
                    if isinstance(date, int):
                        print("PROBLEM: date is int")
                        print(date)
                        # breakpoint()
                    # print(source)
                    # print(date)
                    await sqlite.add_entry_and_set_date(
                        db_file, source, entry)
                #     print(current_time(), entry, title)
                # else:
                #     print(current_time(), exist, title)


async def remove_nonexistent_entries(db_file, feed, source):
    """
    Remove entries that don't exist in a given parsed feed.
    Check the entries returned from feed and delete read non
    existing entries, otherwise move to table archive, if unread.

    Parameters
    ----------
    db_file : str
        Path to database file.
    feed : list
        Parsed feed document.
    source : str
        Feed URL. URL of associated feed.
    """
    items = await sqlite.get_entries_of_source(db_file, feed, source)
    entries = feed.entries
    # breakpoint()
    for item in items:
        valid = False
        for entry in entries:
            title = None
            link = None
            time = None
            # valid = False
            # TODO better check and don't repeat code
            if entry.has_key("id") and item[3]:
                if entry.id == item[3]:
                    # print("compare1:", entry.id)
                    # print("compare2:", item[3])
                    # print("============")
                    valid = True
                    break
            else:
                if entry.has_key("title"):
                    title = entry.title
                else:
                    title = feed["feed"]["title"]
                if entry.has_key("link"):
                    link = join_url(source, entry.link)
                else:
                    link = source
                if entry.has_key("published") and item[4]:
                    # print("compare11:", title, link, time)
                    # print("compare22:", item[1], item[2], item[4])
                    # print("============")
                    time = rfc2822_to_iso8601(entry.published)
                    if (item[1] == title and
                        item[2] == link and
                        item[4] == time):
                        valid = True
                        break
                else:
                    if (item[1] == title and
                        item[2] == link):
                        # print("compare111:", title, link)
                        # print("compare222:", item[1], item[2])
                        # print("============")
                        valid = True
                        break
            # TODO better check and don't repeat code
        if not valid:
            # print("id:        ", item[0])
            # if title:
            #     print("title:     ", title)
            #     print("item[1]:   ", item[1])
            # if link:
            #     print("link:      ", link)
            #     print("item[2]:   ", item[2])
            # if entry.id:
            #     print("last_entry:", entry.id)
            #     print("item[3]:   ", item[3])
            # if time:
            #     print("time:      ", time)
            #     print("item[4]:   ", item[4])
            # print("read:      ", item[5])
            # breakpoint()

            # TODO Send to table archive
            # TODO Also make a regular/routine check for sources that
            #      have been changed (though that can only happen when
            #      manually editing)
            ix = item[0]
            # print(">>> SOURCE: ", source)
            # print(">>> INVALID:", item[1])
            # print("title:", item[1])
            # print("link :", item[2])
            # print("id   :", item[3])
            if item[5] == 1:
                sqlite.delete_entry_by_id(db_file, ix)
                # print(">>> DELETING:", item[1])
            else:
                # print(">>> ARCHIVING:", item[1])
                sqlite.archive_entry(db_file, ix)
        limit = (
            await sqlite.get_settings_value(db_file, "archive")
            ) or (
            config.get_value_default("settings", "Settings", "archive")
            )
        await sqlite.maintain_archive(db_file, limit)
