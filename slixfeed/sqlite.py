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
from datetime import date
import logging
import slixfeed.config as config
# from slixfeed.data import join_url
from slixfeed.datetime import (
    current_time,
    rfc2822_to_iso8601
    )
from sqlite3 import connect, Error, IntegrityError
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
        conn.execute("PRAGMA foreign_keys = ON")
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
        feeds_table_sql = (
            """
            CREATE TABLE IF NOT EXISTS feeds (
                id INTEGER NOT NULL,
                name TEXT,
                url TEXT NOT NULL UNIQUE,
                PRIMARY KEY ("id")
              );
            """
            )
        properties_table_sql = (
            """
            CREATE TABLE IF NOT EXISTS properties (
                id INTEGER NOT NULL,
                feed_id INTEGER NOT NULL,
                type TEXT,
                encoding TEXT,
                language TEXT,
                entries INTEGER,
                FOREIGN KEY ("feed_id") REFERENCES "feeds" ("id")
                  ON UPDATE CASCADE
                  ON DELETE CASCADE,
                PRIMARY KEY (id)
              );
            """
            )
        status_table_sql = (
            """
            CREATE TABLE IF NOT EXISTS status (
                id INTEGER NOT NULL,
                feed_id INTEGER NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                updated TEXT,
                scanned TEXT,
                renewed TEXT,
                status_code INTEGER,
                valid INTEGER,
                filter INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY ("feed_id") REFERENCES "feeds" ("id")
                  ON UPDATE CASCADE
                  ON DELETE CASCADE,
                PRIMARY KEY ("id")
              );
            """
            )
        # TODO
        # Consider parameter unique:
        # entry_id TEXT NOT NULL UNIQUE,
        # Will eliminate function:
        # check_entry_exist
        entries_table_sql = (
            """
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER NOT NULL,
                title TEXT NOT NULL,
                link TEXT NOT NULL,
                entry_id TEXT NOT NULL,
                feed_id INTEGER NOT NULL,
                timestamp TEXT,
                read INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY ("feed_id") REFERENCES "feeds" ("id")
                  ON UPDATE CASCADE
                  ON DELETE CASCADE,
                PRIMARY KEY ("id")
              );
            """
            )
        archive_table_sql = (
            """
            CREATE TABLE IF NOT EXISTS archive (
                id INTEGER NOT NULL,
                title TEXT NOT NULL,
                link TEXT NOT NULL,
                entry_id TEXT NOT NULL,
                feed_id INTEGER NOT NULL,
                timestamp TEXT,
                read INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY ("feed_id") REFERENCES "feeds" ("id")
                  ON UPDATE CASCADE
                  ON DELETE CASCADE,
                PRIMARY KEY ("id")
              );
            """
            )
        # statistics_table_sql = (
        #     """
        #     CREATE TABLE IF NOT EXISTS statistics (
        #         id INTEGER NOT NULL,
        #         title TEXT NOT NULL,
        #         number INTEGER,
        #         PRIMARY KEY ("id")
        #       );
        #     """
        #     )
        settings_table_sql = (
            """
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value INTEGER,
                PRIMARY KEY ("id")
              );
            """
            )
        filters_table_sql = (
            """
            CREATE TABLE IF NOT EXISTS filters (
                id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                PRIMARY KEY ("id")
              );
            """
            )
        cur = conn.cursor()
        # cur = get_cursor(db_file)
        cur.execute(feeds_table_sql)
        cur.execute(status_table_sql)
        cur.execute(properties_table_sql)
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


async def import_feeds(db_file, feeds):
    """
    Insert a new feed into the feeds table.

    Parameters
    ----------
    db_file : str
        Path to database file.
    feeds : list
        Set of feeds (Title and URL).
    """
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            for feed in feeds:
                url = feed[0]
                title = feed[1]
                feed = (
                    title, url
                    )
                sql = (
                    """
                    INSERT
                    INTO feeds(
                        name, url)
                    VALUES(
                        ?, ?)
                    """
                    )
                try:
                    cur.execute(sql, feed)
                except IntegrityError as e:
                    logging.warning("Skipping: " + url)
                    logging.error(e)


async def insert_feed(
    db_file, url, title=None, entries=None, version=None,
    encoding=None, language=None, status_code=None, updated=None):
    """
    Insert a new feed into the feeds table.

    Parameters
    ----------
    db_file : str
        Path to database file.
    url : str
        URL.
    title : str, optional
        Feed title. The default is None.
    entries : int, optional
        Number of entries. The default is None.
    version : str, optional
        Type of feed. The default is None.
    encoding : str, optional
        Encoding of feed. The default is None.
    language : str, optional
        Language code of feed. The default is None.
    status : str, optional
        HTTP status code. The default is None.
    updated : ???, optional
        Date feed was last updated. The default is None.
    """
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            feed = (
                title, url
                )
            sql = (
                """
                INSERT
                INTO feeds(
                    name, url)
                VALUES(
                    ?, ?)
                """
                )
            cur.execute(sql, feed)
            sql = (
                """
                SELECT id
                FROM feeds
                WHERE url = :url
                """
                )
            feed_id = cur.execute(sql, (url,)).fetchone()[0]
            status = (
                feed_id, 1, updated, status_code, 1
                )
            sql = (
                """
                INSERT
                INTO status(
                    feed_id, enabled, updated, status_code, valid)
                VALUES(
                    ?, ?, ?, ?, ?)
                """
                )
            cur.execute(sql, status)
            properties = (
                feed_id, entries, version, encoding, language
                )
            sql = (
                """
                INSERT
                INTO properties(
                    feed_id, entries, type, encoding, language)
                VALUES(
                    ?, ?, ?, ?, ?)
                """
                )
            cur.execute(sql, properties)


async def remove_feed_by_url(db_file, url):
    """
    Delete a feed by feed URL.

    Parameters
    ----------
    db_file : str
        Path to database file.
    url : str
        URL of feed.
    """
    with create_connection(db_file) as conn:
        async with DBLOCK:
            cur = conn.cursor()
            sql = (
                """
                DELETE FROM feeds
                WHERE url = ?
                """
                )
            cur.execute(sql, (url,))


async def remove_feed_by_index(db_file, ix):
    """
    Delete a feed by feed ID.

    Parameters
    ----------
    db_file : str
        Path to database file.
    ix : str
        Index of feed.
    """
    with create_connection(db_file) as conn:
        async with DBLOCK:
            cur = conn.cursor()
            sql = (
                """
                SELECT url
                FROM feeds
                WHERE id = ?
                """
                )
            url = cur.execute(sql, (ix,)).fetchone()[0]
            # # NOTE Should we move DBLOCK to this line? 2022-12-23
            # sql = (
            #     "DELETE "
            #     "FROM entries "
            #     "WHERE feed_id = ?"
            #     )
            # cur.execute(sql, (url,)) # Error? 2024-01-05
            # sql = (
            #     "DELETE "
            #     "FROM archive "
            #     "WHERE feed_id = ?"
            #     )
            # cur.execute(sql, (url,))
            sql = (
                """
                DELETE FROM feeds
                WHERE id = ?
                """
                )
            cur.execute(sql, (ix,))
            return url


async def get_feed_id_and_name(db_file, url):
    """
    Get Id and Name of feed.
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
        """
        SELECT id, name
        FROM feeds
        WHERE url = ?
        """
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
            """
            SELECT count(id)
            FROM {}
            """
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
            """
            SELECT count(id)
            FROM status
            WHERE enabled = 1
            """
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
            """
            SELECT
            (
                SELECT count(id)
                FROM entries
                WHERE read = 0
            ) + (
                SELECT count(id)
                FROM archive
            )
            AS total_count
            """
            )
        count = cur.execute(sql).fetchone()[0]
        return count


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
    results : ???
        News items.
    """
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT id, title, link, feed_id, timestamp
            FROM entries
            WHERE read = 0
            UNION ALL
            SELECT id, title, link, feed_id, timestamp
            FROM archive
            ORDER BY timestamp
            DESC LIMIT :num
            """
            )
        results = cur.execute(sql, (num,)).fetchall()
        return results


async def get_feed_id(cur, url):
    """
    Get index of given feed.

    Parameters
    ----------
    cur : object
        Cursor object.
    url : str
        URL.

    Returns
    -------
    feed_id : str
        Feed index.
    """
    sql = (
        """
        SELECT id
        FROM feeds
        WHERE url = :url
        """
        )
    feed_id = cur.execute(sql, (url,)).fetchone()[0]
    return feed_id


async def mark_entry_as_read(cur, ix):
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
        """
        UPDATE entries
        SET read = 1
        WHERE id = ?
        """
        )
    cur.execute(sql, (ix,))


async def mark_feed_as_read(db_file, url):
    """
    Set read status of entries of given feed as read.

    Parameters
    ----------
    db_file : str
        Path to database file.
    url : str
        URL.
    """
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = (
                """
                UPDATE entries
                SET read = 1
                WHERE feed_id = ?
                """
                )
            cur.execute(sql, (url,))


async def delete_entry_by_id(db_file, ix):
    """
    Delete entry by Id.

    Parameters
    ----------
    db_file : str
        Path to database file.
    ix : str
        Index.
    """
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = (
                """
                DELETE
                FROM entries
                WHERE id = :ix
                """
                )
            cur.execute(sql, (ix,))


async def archive_entry(db_file, ix):
    """
    Insert entry to archive and delete entry.

    Parameters
    ----------
    db_file : str
        Path to database file.
    ix : str
        Index.
    """
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = (
                """
                INSERT
                INTO archive
                SELECT *
                FROM entries
                WHERE entries.id = :ix
                """
                )
            try:
                cur.execute(sql, (ix,))
            except:
                print(
                    "ERROR DB insert from entries "
                    "into archive at index", ix
                    )
            sql = (
                """
                DELETE
                FROM entries
                WHERE id = :ix
                """
                )
            try:
                cur.execute(sql, (ix,))
            except:
                print(
                    "ERROR DB deleting items from "
                    "table entries at index", ix
                    )


def get_feed_title(db_file, ix):
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT name
            FROM feeds
            WHERE id = :ix
            """
            )
        title = cur.execute(sql, (ix,)).fetchone()[0]
        return title


# TODO Handletable archive too
def get_entry_url(db_file, ix):
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT link
            FROM entries
            WHERE id = :ix
            """
            )
        url = cur.execute(sql, (ix,)).fetchone()[0]
        return url


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
            await mark_entry_as_read(cur, ix)
            await delete_archived_entry(cur, ix)


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
                """
                UPDATE entries
                SET read = 1
                """
                )
            cur.execute(sql)
            sql = (
                """
                DELETE
                FROM archive
                """
                )
            cur.execute(sql)


async def delete_archived_entry(cur, ix):
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
        """
        DELETE FROM archive
        WHERE id = ?
        """
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
                value = "Default"
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


async def set_enabled_status(db_file, ix, status):
    """
    Set status of feed to enabled or not enabled (i.e. disabled).

    Parameters
    ----------
    db_file : str
        Path to database file.
    ix : str
        Index of entry.
    status : int
        0 or 1.
    """
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = (
                """
                UPDATE feeds
                SET enabled = :status
                WHERE id = :id
                """
                )
            cur.execute(sql, {
                "status": status,
                "id": ix
                })


"""
TODO

Investigate what causes date to be int 0

NOTE

When time functions of slixfeed.timedate
were async, there were errors of coroutines

"""
async def add_entry(
    db_file, title, link, entry_id, url, date, read_status):
    """
    Add a new entry row into the entries table.

    Parameters
    ----------
    db_file : str
        Path to database file.
    title : str
        Title.
    link : str
        Link.
    entry_id : str
        Entry index.
    url : str
        URL.
    date : str
        Date.
    read_status : str
        0 or 1.
    """
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = (
                """
                SELECT id
                FROM feeds
                WHERE url = :url
                """
                )
            feed_id = cur.execute(sql, (url,)).fetchone()[0]
            sql = (
                """
                INSERT
                INTO entries(
                    title, link, entry_id, feed_id, timestamp, read)
                VALUES(
                    :title, :link, :entry_id, :feed_id, :timestamp, :read)
                """
                )
            cur.execute(sql, {
                "title": title,
                "link": link,
                "entry_id": entry_id,
                "feed_id": feed_id,
                "timestamp": date,
                "read": read_status
                })
            # try:
            #     cur.execute(sql, entry)
            # except:
            #     # None
            #     print("Unknown error for sqlite.add_entry")
            #     print(entry)
            #     #
            #     # print(current_time(), "COROUTINE OBJECT NOW")
            #     # for i in entry:
            #     #     print(type(i))
            #     #     print(i)
            #     # print(type(entry))
            #     # print(entry)
            #     # print(current_time(), "COROUTINE OBJECT NOW")
            #     # breakpoint()


async def set_date(db_file, url):
    """
    Set renewed date of given feed.

    Parameters
    ----------
    db_file : str
        Path to database file.
    url : str
        URL.
    """
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = (
                """
                SELECT id
                FROM feeds
                WHERE url = :url
                """
                )
            feed_id = cur.execute(sql, (url,)).fetchone()[0]
            sql = (
                """
                UPDATE status
                SET renewed = :today
                WHERE feed_id = :feed_id
                """
                )
            # cur = conn.cursor()
            cur.execute(sql, {
                "today": date.today(),
                "feed_id": feed_id
                })


async def update_feed_status(db_file, url, status_code):
    """
    Set status_code of feed_id in table status.

    Parameters
    ----------
    db_file : str
        Path to database file.
    url : str
        Feed URL.
    status : str
        Status ID or message.
    """
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = (
                """
                SELECT id
                FROM feeds
                WHERE url = :url
                """
                )
            # try:
            feed_id = cur.execute(sql, (url,)).fetchone()[0]
            # except:
            #     breakpoint()
            sql = (
                """
                UPDATE status
                SET status_code = :status_code, scanned = :scanned
                WHERE feed_id = :feed_id
                """
                )
            cur.execute(sql, {
                "status_code": status_code,
                "scanned": date.today(),
                "feed_id": feed_id
                })


async def update_feed_validity(db_file, url, valid):
    """
    Set validity status of feed_id in table status.

    Parameters
    ----------
    db_file : str
        Path to database file.
    url : str
        Feed URL.
    valid : boolean
        0 or 1.
    """
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = (
                """
                SELECT id
                FROM feeds
                WHERE url = :url
                """
                )
            feed_id = cur.execute(sql, (url,)).fetchone()[0]
            sql = (
                """
                UPDATE status
                SET valid = :valid
                WHERE feed_id = :feed_id
                """
                )
            cur.execute(sql, {
                "valid": valid,
                "feed_id": feed_id
                })


async def update_feed_properties(db_file, url, entries, updated):
    """
    Update properties of url in table feeds.

    Parameters
    ----------
    db_file : str
        Path to database file.
    url : str
        Feed URL.
    entries : int
        Number of entries.
    updated : ???
        Date feed was last updated.
    """
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = (
                """
                SELECT id
                FROM feeds
                WHERE url = :url
                """
                )
            feed_id = cur.execute(sql, (url,)).fetchone()[0]
            sql = (
                """
                UPDATE properties
                SET entries = :entries
                WHERE feed_id = :feed_id
                """
                )
            cur.execute(sql, {
                "entries"  : entries,
                "feed_id": feed_id
                })


async def maintain_archive(db_file, limit):
    """
    Maintain list of archived entries equal to specified number of items.

    Parameters
    ----------
    db_file : str
        Path to database file.
    limit : str
        Number of maximum entries to store.
    """
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = (
                """
                SELECT count(id)
                FROM archive
                """
                )
            count = cur.execute(sql).fetchone()[0]
            # FIXME Upon first time joining to a groupchat
            # and then adding a URL, variable "limit"
            # becomes a string in one of the iterations.
            # if isinstance(limit,str):
            #     print("STOP")
            #     breakpoint()
            difference = count - int(limit)
            if difference > 0:
                sql = (
                    """
                    DELETE FROM archive
                    WHERE id
                    IN (SELECT id
                    FROM archive
                    ORDER BY timestamp ASC
                    LIMIT :difference)
                    """
                    )
                cur.execute(sql, {
                    "difference": difference
                    })


# TODO Move entries that don't exist into table archive.
# NOTE Entries that are read from archive are deleted.
# NOTE Unlike entries from table entries, entries from
#      table archive are not marked as read.
async def get_entries_of_feed(db_file, feed, url):
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
    url : str
        Feed URL. URL of associated feed.
    """
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT id, title, link, entry_id, timestamp, read
            FROM entries
            WHERE feed_id = ?
            """
            )
        items = cur.execute(sql, (url,)).fetchall()
        return items


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

# TODO select by "feed_id" (of table "status") from
# "feed" urls that are enabled in table "status"
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
            """
            SELECT url
            FROM feeds
            """
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
    results : ???
        URLs of feeds.
    """
    # TODO
    # 1) Select id from table feeds
    #    Select name, url (feeds) updated, enabled, feed_id (status)
    # 2) Sort feeds by id. Sort status by feed_id
    # results += cur.execute(sql).fetchall()
    cur = get_cursor(db_file)
    sql = (
        """
        SELECT name, url, id
        FROM feeds
        """
        )
    results = cur.execute(sql).fetchall()
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
        """
        SELECT title, link, timestamp
        FROM entries
        WHERE read = 0
        UNION ALL
        SELECT title, link, timestamp
        FROM archive
        WHERE read = 0
        ORDER BY timestamp DESC
        LIMIT :num
        """
        )
    results = cur.execute(
        sql, (num,)).fetchall()
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
        """
        SELECT name, id, url
        FROM feeds
        WHERE name LIKE ?
        OR url LIKE ?
        LIMIT 50
        """
        )
    results = cur.execute(
        sql, [f'%{query}%', f'%{query}%']).fetchall()
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
        """
        SELECT title, link
        FROM entries
        WHERE title LIKE ?
        UNION ALL
        SELECT title, link
        FROM archive
        WHERE title LIKE ?
        LIMIT 50
        """
        )
    results = cur.execute(
        sql, (f'%{query}%', f'%{query}%')).fetchall()
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
async def check_entry_exist(
    db_file, url, entry_id=None, title=None, link=None, date=None):
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
    entry_id : str, optional
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
    exist = False
    if entry_id:
        sql = (
            """
            SELECT id
            FROM feeds
            WHERE url = :url
            """
            )
        feed_id = cur.execute(sql, (url,)).fetchone()[0]
        sql = (
            """
            SELECT id
            FROM entries
            WHERE
            entry_id = :entry_id and
            feed_id = :feed_id
            """
            )
        result = cur.execute(sql, {
            "entry_id": entry_id,
            "feed_id": feed_id
            }).fetchone()
        if result: exist = True
    elif date:
        sql = (
            """
            SELECT id
            FROM entries
            WHERE
            title = :title and
            link = :link and
            timestamp = :date
            """
            )
        try:
            result = cur.execute(sql, {
                "title": title,
                "link": link,
                "timestamp": date
                }).fetchone()
            if result: exist = True
        except:
            print(current_time(), "ERROR DATE: source =", url)
            print(current_time(), "ERROR DATE: date =", date)
    else:
        sql = (
            """
            SELECT id
            FROM entries
            WHERE
            title = :title and
            link = :link
            """
            )
        result = cur.execute(sql, {
            "title": title,
            "link": link
            }).fetchone()
        if result: exist = True
    # try:
    #     if result:
    #         return True
    #     else:
    #         return None
    # except:
    #     print(current_time(), "ERROR DATE: result =", url)
    return exist


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
            # try:
            sql = (
                """
                UPDATE settings
                SET value = :value
                WHERE key = :key
                """
                )
            cur.execute(sql, {
                "key": key,
                "value": value
                })
            # except:
            #     logging.debug(
            #         "No specific value set for key {}.".format(key)
            #         )


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
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        try:
            sql = (
                """
                SELECT value
                FROM settings
                WHERE key = ?
                """
                )
            value = cur.execute(sql, (key,)).fetchone()[0]
            return value
        except:
            logging.debug(
                "No specific value set for key {}.".format(key)
                )


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
            sql = (
                """
                UPDATE filters
                SET value = :value
                WHERE key = :key
                """
                )
            cur.execute(sql, {
                "key": key,
                "value": val
                })


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
        cur = conn.cursor()
        try:
            sql = (
                """
                SELECT value
                FROM filters
                WHERE key = ?
                """
                )
            value = cur.execute(sql, (key,)).fetchone()[0]
            return value
        except:
            logging.debug(
                "No specific value set for key {}.".format(key)
                )
