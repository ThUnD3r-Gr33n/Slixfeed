#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

TODO

1) Table feeds:
    category
    type (atom, rdf, rss0.9. rss2 etc.)

2) Function mark_all_read for entries of given feed

3) Statistics

"""

from asyncio import Lock
from bs4 import BeautifulSoup
from datetime import date
# from slixfeed.config import get_value_default
import slixfeed.config as config
# from slixfeed.data import join_url
from slixfeed.datetime import (
    current_time,
    rfc2822_to_iso8601
    )
from sqlite3 import connect, Error
from slixfeed.url import join_url

# from eliot import start_action, to_file
# # with start_action(action_type="list_feeds()", db=db_file):
# # with start_action(action_type="last_entries()", num=num):
# # with start_action(action_type="get_feeds()"):
# # with start_action(action_type="remove_entry()", source=source):
# # with start_action(action_type="search_entries()", query=query):
# # with start_action(action_type="check_entry()", link=link):

# aiosqlite
DBLOCK = Lock()

CURSORS = {}

def create_connection(db_file):
    """
    Create a database connection to the SQLite database
    specified by db_file.

    Parameters
    ----------
    db_file : str
        Path to database file.

    Returns
    -------
    conn : object
        Connection object or None.
    """
    conn = None
    try:
        conn = connect(db_file)
        return conn
    except Error as e:
        print(e)
    return conn


def create_tables(db_file):
    """
    Create SQLite tables.

    Parameters
    ----------
    db_file : str
        Path to database file.
    """
    with create_connection(db_file) as conn:
        feeds_table_sql =(
            "CREATE TABLE IF NOT EXISTS feeds ("
            "id INTEGER PRIMARY KEY,"
            "name TEXT,"
            "address TEXT NOT NULL,"
            "enabled INTEGER NOT NULL,"
            "scanned TEXT,"
            "updated TEXT,"
            "status INTEGER,"
            "valid INTEGER"
            ");"
            )
        entries_table_sql = (
            "CREATE TABLE IF NOT EXISTS entries ("
            "id INTEGER PRIMARY KEY,"
            "title TEXT NOT NULL,"
            "link TEXT NOT NULL,"
            "entry_id TEXT,"
            "source TEXT NOT NULL,"
            "timestamp TEXT,"
            "read INTEGER"
            ");"
            )
        archive_table_sql = (
            "CREATE TABLE IF NOT EXISTS archive ("
            "id INTEGER PRIMARY KEY,"
            "title TEXT NOT NULL,"
            "link TEXT NOT NULL,"
            "entry_id TEXT,"
            "source TEXT NOT NULL,"
            "timestamp TEXT,"
            "read INTEGER"
            ");"
            )
        # statistics_table_sql = (
        #     "CREATE TABLE IF NOT EXISTS statistics ("
        #     "id INTEGER PRIMARY KEY,"
        #     "title TEXT NOT NULL,"
        #     "number INTEGER"
        #     ");"
        #     )
        settings_table_sql = (
            "CREATE TABLE IF NOT EXISTS settings ("
            "id INTEGER PRIMARY KEY,"
            "key TEXT NOT NULL,"
            "value INTEGER"
            ");"
            )
        filters_table_sql = (
            "CREATE TABLE IF NOT EXISTS filters ("
            "id INTEGER PRIMARY KEY,"
            "key TEXT NOT NULL,"
            "value TEXT"
            ");"
            )
        cur = conn.cursor()
        # cur = get_cursor(db_file)
        cur.execute(feeds_table_sql)
        cur.execute(entries_table_sql)
        cur.execute(archive_table_sql)
        # cur.execute(statistics_table_sql)
        cur.execute(settings_table_sql)
        cur.execute(filters_table_sql)


def get_cursor(db_file):
    """
    Allocate a cursor to connection per database.

    Parameters
    ----------
    db_file : str
        Path to database file.

    Returns
    -------
    CURSORS[db_file] : object
        Cursor.
    """
    if db_file in CURSORS:
        return CURSORS[db_file]
    else:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            CURSORS[db_file] = cur
    return CURSORS[db_file]


async def insert_feed(db_file, url, title=None, status=None):
    """
    Insert a new feed into the feeds table.

    Parameters
    ----------
    db_file : str
        Path to database file.
    url : str
        URL.
    title : str, optional
        Feed Title. The default is None.
    status : str, optional
        HTTP status code. The default is None.

    Returns
    -------
    msg : str
        Message.
    """
    #TODO consider async with DBLOCK
    #conn = create_connection(db_file)

    # with create_connection(db_file) as conn:
    #     #exist = await check_feed_exist(conn, url)
    #     exist = await check_feed_exist(db_file, url)

    # if not exist:
    #     status = await main.download_feed(url)
    # else:
    #     return "News source is already listed in the subscription list"

    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            # title = feed["feed"]["title"]
            feed = (title, url, 1, status, 1)
            sql = (
                "INSERT INTO feeds("
                "name, address, enabled, status, valid"
                ")"
                "VALUES(?, ?, ?, ?, ?) "
                )
            cur.execute(sql, feed)

    source = title if title else '<' + url + '>'
    msg = (
        "> {}\nNews source \"{}\" has been added "
        "to subscription list."
        ).format(url, source)
    return msg


async def remove_feed(db_file, ix):
    """
    Delete a feed by feed ID.

    Parameters
    ----------
    db_file : str
        Path to database file.
    ix : str
        Index of feed.

    Returns
    -------
    msg : str
        Message.
    """
    with create_connection(db_file) as conn:
        async with DBLOCK:
            cur = conn.cursor()
            try:
                sql = (
                    "SELECT address "
                    "FROM feeds "
                    "WHERE id = ?"
                    )
                # cur
                # for i in url:
                #     url = i[0]
                url = cur.execute(sql, (ix,)).fetchone()[0]
                sql = (
                    "SELECT name "
                    "FROM feeds "
                    "WHERE id = ?"
                    )
                name = cur.execute(sql, (ix,)).fetchone()[0]
                # NOTE Should we move DBLOCK to this line? 2022-12-23
                sql = (
                    "DELETE "
                    "FROM entries "
                    "WHERE source = ?"
                    )
                cur.execute(sql, (url,))
                sql = (
                    "DELETE "
                    "FROM archive "
                    "WHERE source = ?"
                    )
                cur.execute(sql, (url,))
                sql = (
                    "DELETE FROM feeds "
                    "WHERE id = ?"
                    )
                cur.execute(sql, (ix,))
                msg = (
                    "> {}\nNews source \"{}\" has been removed "
                    "from subscription list."
                    ).format(url, name)
            except:
                msg = (
                    "No news source with ID {}."
                    ).format(ix)
    return msg


async def check_feed_exist(db_file, url):
    """
    Check whether a feed exists.
    Query for feeds by given url.

    Parameters
    ----------
    db_file : str
        Path to database file.
    url : str
        URL.

    Returns
    -------
    result : list
        List of ID and Name of feed.
    """
    cur = get_cursor(db_file)
    sql = (
        "SELECT id, name "
        "FROM feeds "
        "WHERE address = ?"
        )
    result = cur.execute(sql, (url,)).fetchone()
    return result


async def get_number_of_items(db_file, table):
    """
    Return number of entries or feeds.

    Parameters
    ----------
    db_file : str
        Path to database file.
    table : str
        "entries" or "feeds".

    Returns
    -------
    count : ?
        Number of rows.
    """
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            "SELECT count(id) "
            "FROM {}"
            ).format(table)
        count = cur.execute(sql).fetchone()[0]
        return count


async def get_number_of_feeds_active(db_file):
    """
    Return number of active feeds.

    Parameters
    ----------
    db_file : str
        Path to database file.

    Returns
    -------
    count : ?
        Number of rows.
    """
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            "SELECT count(id) "
            "FROM feeds "
            "WHERE enabled = 1"
            )
        count = cur.execute(sql).fetchone()[0]
        return count


async def get_number_of_entries_unread(db_file):
    """
    Return number of unread items.

    Parameters
    ----------
    db_file : str
        Path to database file.

    Returns
    -------
    count : ?
        Number of rows.
    """
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            "SELECT "
            "("
            "SELECT count(id) "
            "FROM entries "
            "WHERE read = 0"
            ") "
            "+ "
            "("
            "SELECT count(id) "
            "FROM archive"
            ") "
            "AS total_count"
            )
        count = cur.execute(sql).fetchone()[0]
        return count


# TODO Read from entries and archives
async def get_unread_entries(db_file, num):
    """
    Extract information from unread entries.

    Parameters
    ----------
    db_file : str
        Path to database file.
    num : str, optional
        Number. The default is None.

    Returns
    -------
    entry : str
        News item message.
    """
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        # sql = (
        #     "SELECT id "
        #     "FROM entries "
        #     "WHERE read = 0 "
        #     "LIMIT 1"
        #     )
        # sql = ("SELECT id "
        #        "FROM entries "
        #        "WHERE read = 0 "
        #        "ORDER BY timestamp DESC "
        #        "LIMIT 1"
        #        )
        # sql = (
        #     "SELECT id, title, summary, link "
        #     "FROM entries "
        #     "WHERE read = 0 "
        #     "ORDER BY timestamp "
        #     "DESC LIMIT :num"
        #     )
        sql = (
            "SELECT id, title, link, source, timestamp "
            "FROM entries "
            "WHERE read = 0 "
            "UNION ALL "
            "SELECT id, title, link, source, timestamp "
            "FROM archive "
            "ORDER BY timestamp "
            "DESC LIMIT :num"
            )
        results = cur.execute(sql, (num,))
        results = results.fetchall()
        # print("### sqlite.get_unread_entries ###")
        # print(results)
        # breakpoint()
        return results


def mark_entry_as_read(cur, ix):
    """
    Set read status of entry as read.

    Parameters
    ----------
    cur : object
        Cursor object.
    ix : str
        Index of entry.
    """
    sql = (
        "UPDATE entries "
        "SET read = 1 "
        "WHERE id = ?"
        )
    cur.execute(sql, (ix,))


async def mark_source_as_read(db_file, source):
    """
    Set read status of entries of given source as read.

    Parameters
    ----------
    db_file : str
        Path to database file.
    source : str
        URL.
    """
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = (
                "UPDATE entries "
                "SET read = 1 "
                "WHERE source = ?"
                )
            cur.execute(sql, (source,))


def get_feed_title(db_file, source):
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            "SELECT name "
            "FROM feeds "
            "WHERE address = :source "
            )
        feed_title = cur.execute(sql, (source,))
        feed_title = feed_title.fetchone()[0]
        return feed_title


async def mark_as_read(db_file, ix):
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            # TODO While `async with DBLOCK` does work well from
            # outside of functions, it would be better practice
            # to place it within the functions.
            # NOTE: We can use DBLOCK once for both
            # functions, because, due to exclusive
            # ID, only one can ever occur.
            mark_entry_as_read(cur, ix)
            delete_archived_entry(cur, ix)

async def mark_all_as_read(db_file):
    """
    Set read status of all entries as read.

    Parameters
    ----------
    db_file : str
        Path to database file.
    """
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = (
                "UPDATE entries "
                "SET read = 1 "
                )
            cur.execute(sql)
            sql = (
                "DELETE FROM archive"
                )
            cur.execute(sql)


def delete_archived_entry(cur, ix):
    """
    Delete entry from table archive.

    Parameters
    ----------
    db_file : str
        Path to database file.
    ix : str
        Index of entry.
    """
    sql = (
        "DELETE FROM archive "
        "WHERE id = ?"
        )
    cur.execute(sql, (ix,))


async def statistics(db_file):
    """
    Return table statistics.

    Parameters
    ----------
    db_file : str
        Path to database file.

    Returns
    -------
    values : list
        List of values.
    """
    values = []
    values.extend([await get_number_of_entries_unread(db_file)])
    entries = await get_number_of_items(db_file, 'entries')
    archive = await get_number_of_items(db_file, 'archive')
    values.extend([entries + archive])
    values.extend([await get_number_of_feeds_active(db_file)])
    values.extend([await get_number_of_items(db_file, 'feeds')])
    # msg = """You have {} unread news items out of {} from {} news sources.
    #       """.format(unread_entries, entries, feeds)
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        for key in ["archive", "interval",
                    "quantum", "enabled"]:
            sql = (
            "SELECT value "
            "FROM settings "
            "WHERE key = ?"
            )
            try:
                value = cur.execute(sql, (key,)).fetchone()[0]
            except:
                print("Error for key:", key)
                value = "none"
            values.extend([value])
    return values


async def update_statistics(cur):
    """
    Update table statistics.

    Parameters
    ----------
    cur : object
        Cursor object.
    """
    stat_dict = {}
    stat_dict["feeds"] = await get_number_of_items(cur, 'feeds')
    stat_dict["entries"] = await get_number_of_items(cur, 'entries')
    stat_dict["unread"] = await get_number_of_entries_unread(cur=cur)
    for i in stat_dict:
        sql = (
            "SELECT id "
            "FROM statistics "
            "WHERE title = ?"
            )
        cur.execute(sql, (i,))
        if cur.fetchone():
            sql = (
                "UPDATE statistics "
                "SET number = :num "
                "WHERE title = :title"
                )
            cur.execute(sql, {
                "title": i,
                "num": stat_dict[i]
                })
        else:
            sql = (
                "SELECT count(id) "
                "FROM statistics"
                )
            count = cur.execute(sql).fetchone()[0]
            ix = count + 1
            sql = (
                "INSERT INTO statistics "
                "VALUES(?,?,?)"
                )
            cur.execute(sql, (ix, i, stat_dict[i]))


async def toggle_status(db_file, ix):
    """
    Toggle status of feed.

    Parameters
    ----------
    db_file : str
        Path to database file.
    ix : str
        Index of entry.

    Returns
    -------
    msg : str
        Message.
    """
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            try:
                #cur = get_cursor(db_file)
                sql = (
                    "SELECT name "
                    "FROM feeds "
                    "WHERE id = :id"
                    )
                title = cur.execute(sql, (ix,)).fetchone()[0]
                sql = (
                    "SELECT enabled "
                    "FROM feeds "
                    "WHERE id = ?"
                    )
                # NOTE [0][1][2]
                status = cur.execute(sql, (ix,)).fetchone()[0]
                # FIXME always set to 1
                # NOTE Maybe because is not integer
                # TODO Reset feed table before further testing
                if status == 1:
                    status = 0
                    state =  "disabled"
                else:
                    status = 1
                    state = "enabled"
                sql = (
                    "UPDATE feeds "
                    "SET enabled = :status "
                    "WHERE id = :id"
                    )
                cur.execute(sql, {
                    "status": status,
                    "id": ix
                    })
                msg = (
                    "Updates from '{}' are now {}."
                       ).format(title, state)
            except:
                msg = (
                    "No news source with ID {}."
                       ).format(ix)
    return msg


async def set_date(cur, url):
    """
    Set last update date of feed.

    Parameters
    ----------
    cur : object
        Cursor object.
    url : str
        URL.
    """
    today = date.today()
    sql = (
        "UPDATE feeds "
        "SET updated = :today "
        "WHERE address = :url"
        )
    # cur = conn.cursor()
    cur.execute(sql, {
        "today": today,
        "url": url
        })


async def add_entry_and_set_date(db_file, source, entry):
    """
    Add an entry to table entries and set date of source in table feeds.

    Parameters
    ----------
    db_file : str
        Path to database file.
    source : str
        Feed URL.
    entry : list
        Entry properties.
    """
    # TODO While `async with DBLOCK` does work well from
    # outside of functions, it would be better practice
    # to place it within the functions.
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            await add_entry(cur, entry)
            await set_date(cur, source)


async def update_source_status(db_file, status, source):
    """
    Set HTTP status of source in table feeds.

    Parameters
    ----------
    db_file : str
        Path to database file.
    source : str
        Feed URL.
    status : str
        Status ID or message.
    """
    sql = (
        "UPDATE feeds "
        "SET status = :status, scanned = :scanned "
        "WHERE address = :url"
        )
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            cur.execute(sql, {
                "status"  : status,
                "scanned" : date.today(),
                "url"     : source
                })


async def update_source_validity(db_file, source, valid):
    """
    Set validity status of source in table feeds.

    Parameters
    ----------
    db_file : str
        Path to database file.
    source : str
        Feed URL.
    valid : boolean
        0 or 1.
    """
    sql = (
        "UPDATE feeds "
        "SET valid = :validity "
        "WHERE address = :url"
        )
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            cur.execute(sql, {
                "validity": valid,
                "url": source
                })

"""
TODO

Investigate why causes entry[6] (date) to be int 0

"""
async def add_entry(cur, entry):
    """
    Add a new entry row into the entries table.

    Parameters
    ----------
    cur : object
        Cursor object.
    entry : str
        Entry properties.
    """
    sql = (
        "INSERT "
        "INTO entries("
                "title, "
                "link, "
                "entry_id, "
                "source, "
                "timestamp, "
                "read"
                ") "
        "VALUES(?, ?, ?, ?, ?, ?)"
        )
    try:
        cur.execute(sql, entry)
    except:
        print("")
        # print("Unknown error for sqlite.add_entry")
        # print(entry)
        # print(current_time(), "COROUTINE OBJECT NOW")
        # for i in entry:
        #     print(type(i))
        #     print(i)
        # print(type(entry))
        # print(entry)
        # print(current_time(), "COROUTINE OBJECT NOW")
        # breakpoint()


async def maintain_archive(cur, limit):
    """
    Maintain list of archived entries equal to specified number of items.

    Parameters
    ----------
    db_file : str
        Path to database file.
    """
    sql = (
        "SELECT count(id) "
        "FROM archive"
        )
    count = cur.execute(sql).fetchone()[0]
    # FIXME Upon first time joining to a groupchat
    # and then adding a URL, variable "limit"
    # becomes a string in one of the iterations.
    # if isinstance(limit,str):
    #     print("STOP")
    #     breakpoint()
    reduc = count - int(limit)
    if reduc > 0:
        sql = (
            "DELETE FROM archive "
            "WHERE id "
            "IN (SELECT id "
            "FROM archive "
            "ORDER BY timestamp ASC "
            "LIMIT :reduc)"
            )
        cur.execute(sql, {
            "reduc": reduc
            })


# TODO Move entries that don't exist into table archive.
# NOTE Entries that are read from archive are deleted.
# NOTE Unlike entries from table entries, entries from
#      table archive are not marked as read.
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
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            "SELECT id, title, link, entry_id, timestamp, read "
            "FROM entries "
            "WHERE source = ?"
            )
        items = cur.execute(sql, (source,)).fetchall()
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
                async with DBLOCK:
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
                        # print(">>> DELETING:", item[1])
                        sql = (
                            "DELETE "
                            "FROM entries "
                            "WHERE id = :ix"
                            )
                        cur.execute(sql, (ix,))
                    else:
                        # print(">>> ARCHIVING:", item[1])
                        sql = (
                            "INSERT "
                            "INTO archive "
                            "SELECT * "
                            "FROM entries "
                            "WHERE entries.id = :ix"
                            )
                        try:
                            cur.execute(sql, (ix,))
                        except:
                            print(
                                "ERROR DB insert from entries "
                                "into archive at index", ix
                                )
                        sql = (
                            "DELETE "
                            "FROM entries "
                            "WHERE id = :ix"
                            )
                        try:
                            cur.execute(sql, (ix,))
                        except:
                            print(
                                "ERROR DB deleting items from "
                                "table entries at index", ix
                                )
        async with DBLOCK:
            limit = await get_settings_value(db_file, "archive")
            await maintain_archive(cur, limit)


# TODO What is this function for? 2024-01-02
# async def get_feeds(db_file):
#     """
#     Query table feeds for Title, URL, Categories, Tags.

#     Parameters
#     ----------
#     db_file : str
#         Path to database file.

#     Returns
#     -------
#     result : list
#         Title, URL, Categories, Tags of feeds.
#     """
#     with create_connection(db_file) as conn:
#         cur = conn.cursor()
#         sql = (
#             "SELECT name, address, type, categories, tags "
#             "FROM feeds"
#             )
#         result = cur.execute(sql).fetchall()
#         return result


async def get_feeds_url(db_file):
    """
    Query active feeds for URLs.

    Parameters
    ----------
    db_file : str
        Path to database file.

    Returns
    -------
    result : list
        URLs of active feeds.
    """
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            "SELECT address "
            "FROM feeds "
            "WHERE enabled = 1"
            )
        result = cur.execute(sql).fetchall()
        return result


async def get_feeds(db_file):
    """
    Query table feeds and list items.

    Parameters
    ----------
    db_file : str
        Path to database file.

    Returns
    -------
    msg : ???
        URLs of feeds.
    """
    cur = get_cursor(db_file)
    sql = (
        "SELECT name, address, updated, enabled, id "
        "FROM feeds"
        )
    results = cur.execute(sql)
    return results


async def last_entries(db_file, num):
    """
    Query entries.

    Parameters
    ----------
    db_file : str
        Path to database file.
    num : str
        Number.

    Returns
    -------
    titles_list : str
        List of recent N entries as message.
    """
    cur = get_cursor(db_file)
    # sql = (
    #     "SELECT title, link "
    #     "FROM entries "
    #     "ORDER BY ROWID DESC "
    #     "LIMIT :num"
    #     )
    sql = (
        "SELECT title, link, timestamp "
        "FROM entries "
        "WHERE read = 0 "
        "UNION ALL "
        "SELECT title, link, timestamp "
        "FROM archive "
        "WHERE read = 0 "
        "ORDER BY timestamp DESC "
        "LIMIT :num "
        )
    results = cur.execute(sql, (num,))
    return results


async def search_feeds(db_file, query):
    """
    Query feeds.

    Parameters
    ----------
    db_file : str
        Path to database file.
    query : str
        Search query.

    Returns
    -------
    titles_list : str
        Feeds of specified keywords as message.
    """
    cur = get_cursor(db_file)
    sql = (
        "SELECT name, address, id, enabled "
        "FROM feeds "
        "WHERE name LIKE ? "
        "OR address LIKE ? "
        "LIMIT 50"
        )
    results = cur.execute(sql, [f'%{query}%', f'%{query}%'])
    return results


async def search_entries(db_file, query):
    """
    Query entries.

    Parameters
    ----------
    db_file : str
        Path to database file.
    query : str
        Search query.

    Returns
    -------
    titles_list : str
        Entries of specified keywords as message.
    """
    cur = get_cursor(db_file)
    sql = (
        "SELECT title, link "
        "FROM entries "
        "WHERE title LIKE ? "
        "UNION ALL "
        "SELECT title, link "
        "FROM archive "
        "WHERE title LIKE ? "
        "LIMIT 50"
        )
    results = cur.execute(sql, (
        f'%{query}%',
        f'%{query}%'
        ))
    return results

"""
FIXME

Error due to missing date, but it appears that date is present:
ERROR DATE: source = https://blog.heckel.io/feed/
ERROR DATE: date = 2008-05-13T13:51:50+00:00
ERROR DATE: result = https://blog.heckel.io/feed/

19:32:05 ERROR DATE: source = https://mwl.io/feed
19:32:05 ERROR DATE: date = 2023-11-30T10:56:39+00:00
19:32:05 ERROR DATE: result = https://mwl.io/feed
19:32:05 ERROR DATE: source = https://mwl.io/feed
19:32:05 ERROR DATE: date = 2023-11-22T16:59:08+00:00
19:32:05 ERROR DATE: result = https://mwl.io/feed
19:32:06 ERROR DATE: source = https://mwl.io/feed
19:32:06 ERROR DATE: date = 2023-11-16T10:33:57+00:00
19:32:06 ERROR DATE: result = https://mwl.io/feed
19:32:06 ERROR DATE: source = https://mwl.io/feed
19:32:06 ERROR DATE: date = 2023-11-09T07:37:57+00:00
19:32:06 ERROR DATE: result = https://mwl.io/feed

"""
async def check_entry_exist(db_file, source, eid=None,
                            title=None, link=None, date=None):
    """
    Check whether an entry exists.
    If entry has an ID, check by ID.
    If entry has timestamp, check by title, link and date.
    Otherwise, check by title and link.

    Parameters
    ----------
    db_file : str
        Path to database file.
    source : str
        Feed URL. URL of associated feed.
    eid : str, optional
        Entry ID. The default is None.
    title : str, optional
        Entry title. The default is None.
    link : str, optional
        Entry URL. The default is None.
    date : str, optional
        Entry Timestamp. The default is None.

    Returns
    -------
    bool
        True or None.
    """
    cur = get_cursor(db_file)
    if eid:
        sql = (
            "SELECT id "
            "FROM entries "
            "WHERE entry_id = :eid and source = :source"
            )
        result = cur.execute(sql, {
            "eid": eid,
            "source": source
            }).fetchone()
    elif date:
        sql = (
            "SELECT id "
            "FROM entries "
            "WHERE "
            "title = :title and "
            "link = :link and "
            "timestamp = :date"
            )
        try:
            result = cur.execute(sql, {
                "title": title,
                "link": link,
                "timestamp": date
                }).fetchone()
        except:
            print(current_time(), "ERROR DATE: source =", source)
            print(current_time(), "ERROR DATE: date =", date)
    else:
        sql = (
            "SELECT id "
            "FROM entries "
            "WHERE title = :title and link = :link"
            )
        result = cur.execute(sql, {
            "title": title,
            "link": link
            }).fetchone()
    try:
        if result:
            return True
        else:
            None
    except:
        print(current_time(), "ERROR DATE: result =", source)


async def set_settings_value(db_file, key_value):
    """
    Set settings value.

    Parameters
    ----------
    db_file : str
        Path to database file.
    key_value : list
         key : str
               enabled, interval, masters, quantum, random.
         value : int
               Numeric value.
    """
    # if isinstance(key_value, list):
    #     key = key_value[0]
    #     val = key_value[1]
    # elif key_value == "enable":
    #     key = "enabled"
    #     val = 1
    # else:
    #     key = "enabled"
    #     val = 0
    key = key_value[0]
    value = key_value[1]
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            await set_settings_value_default(cur, key)
            sql = (
                "UPDATE settings "
                "SET value = :value "
                "WHERE key = :key"
                )
            cur.execute(sql, {
                "key": key,
                "value": value
                })


async def set_settings_value_default(cur, key):
    """
    Set default settings value, if no value found.

    Parameters
    ----------
    cur : object
        Cursor object.
    key : str
        Key: enabled, interval, master, quantum, random.

    Returns
    -------
    val : str
        Numeric value.
    """
# async def set_settings_value_default(cur):
#     keys = ["enabled", "interval", "quantum"]
#     for i in keys:
#         sql = "SELECT id FROM settings WHERE key = ?"
#         cur.execute(sql, (i,))
#         if not cur.fetchone():
#             val = settings.get_value_default(i)
#             sql = "INSERT INTO settings(key,value) VALUES(?,?)"
#             cur.execute(sql, (i, val))
    sql = (
        "SELECT id "
        "FROM settings "
        "WHERE key = ?"
        )
    cur.execute(sql, (key,))
    if not cur.fetchone():
        value = config.get_value_default("settings", "Settings", key)
        sql = (
            "INSERT "
            "INTO settings(key,value) "
            "VALUES(?,?)"
            )
        cur.execute(sql, (key, value))
        return value


async def get_settings_value(db_file, key):
    """
    Get settings value.

    Parameters
    ----------
    db_file : str
        Path to database file.
    key : str
        Key: archive, enabled, filter-allow, filter-deny,
             interval, length, old, quantum, random.

    Returns
    -------
    val : str
        Numeric value.
    """
    # try:
    #     with create_connection(db_file) as conn:
    #         cur = conn.cursor()
    #         sql = "SELECT value FROM settings WHERE key = ?"
    #         cur.execute(sql, (key,))
    #         result = cur.fetchone()
    # except:
    #     result = settings.get_value_default(key)
    # if not result:
    #     result = settings.get_value_default(key)
    # return result
    with create_connection(db_file) as conn:
        try:
            cur = conn.cursor()
            sql = (
                "SELECT value "
                "FROM settings "
                "WHERE key = ?"
                )
            val = cur.execute(sql, (key,)).fetchone()[0]
        except:
            val = await set_settings_value_default(cur, key)
        if not val:
            val = await set_settings_value_default(cur, key)
        return val


async def set_filters_value(db_file, key_value):
    """
    Set settings value.

    Parameters
    ----------
    db_file : str
        Path to database file.
    key_value : list
         key : str
               filter-allow, filter-deny, filter-replace.
         value : int
               Numeric value.
    """
    # if isinstance(key_value, list):
    #     key = key_value[0]
    #     val = key_value[1]
    # elif key_value == "enable":
    #     key = "enabled"
    #     val = 1
    # else:
    #     key = "enabled"
    #     val = 0
    key = key_value[0]
    val = key_value[1]
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            await set_filters_value_default(cur, key)
            sql = (
                "UPDATE filters "
                "SET value = :value "
                "WHERE key = :key"
                )
            cur.execute(sql, {
                "key": key,
                "value": val
                })


async def set_filters_value_default(cur, key):
    """
    Set default filters value, if no value found.

    Parameters
    ----------
    cur : object
        Cursor object.
    key : str
        Key: filter-allow, filter-deny, filter-replace.

    Returns
    -------
    val : str
        List of strings.
    """
    sql = (
        "SELECT id "
        "FROM filters "
        "WHERE key = ?"
        )
    cur.execute(sql, (key,))
    if not cur.fetchone():
        val = config.get_list("lists.yaml")
        val = val[key]
        val = ",".join(val)
        sql = (
            "INSERT "
            "INTO filters(key,value) "
            "VALUES(?,?)"
            )
        cur.execute(sql, (key, val))
        return val


async def get_filters_value(db_file, key):
    """
    Get filters value.

    Parameters
    ----------
    db_file : str
        Path to database file.
    key : str
        Key: allow, deny.

    Returns
    -------
    val : str
        List of strings.
    """
    with create_connection(db_file) as conn:
        try:
            cur = conn.cursor()
            sql = (
                "SELECT value "
                "FROM filters "
                "WHERE key = ?"
                )
            val = cur.execute(sql, (key,)).fetchone()[0]
        except:
            val = await set_filters_value_default(cur, key)
        if not val:
            val = await set_filters_value_default(cur, key)
        return val
