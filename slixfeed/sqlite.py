#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

TODO

1) Function to open connection (receive db_file).
   Function to close connection.
   All other functions to receive cursor.

2) Merge function add_metadata into function import_feeds.

3) SQL prepared statements.

4) Support categories;

"""

from asyncio import Lock
# from slixfeed.data import join_url
from slixfeed.log import Logger
from sqlite3 import connect, Error, IntegrityError
import sys
import time

# from eliot import start_action, to_file
# # with start_action(action_type="list_feeds()", db=db_file):
# # with start_action(action_type="last_entries()", num=num):
# # with start_action(action_type="get_feeds()"):
# # with start_action(action_type="remove_entry()", source=source):
# # with start_action(action_type="search_entries()", query=query):
# # with start_action(action_type="check_entry()", link=link):

CURSORS = {}

# aiosqlite
DBLOCK = Lock()

logger = Logger(__name__)

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
    time_begin = time.time()
    function_name = sys._getframe().f_code.co_name
    message_log = '{}'
    logger.debug(message_log.format(function_name))
    conn = None
    try:
        conn = connect(db_file)
        conn.execute("PRAGMA foreign_keys = ON")
        # return conn
    except Error as e:
        print(e)
    time_end = time.time()
    difference = time_end - time_begin
    if difference > 1: logger.warning('{} (time: {})'.format(function_name,
                                                             difference))
    return conn


def create_tables(db_file):
    """
    Create SQLite tables.

    Parameters
    ----------
    db_file : str
        Path to database file.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {}'
                .format(function_name, db_file))
    with create_connection(db_file) as conn:
        archive_table_sql = (
            """
            CREATE TABLE IF NOT EXISTS archive (
                id INTEGER NOT NULL,
                title TEXT NOT NULL,
                link TEXT NOT NULL,
                summary TEXT,
                enclosure TEXT,
                entry_id TEXT NOT NULL,
                feed_id INTEGER NOT NULL,
                timestamp TEXT,
                read INTEGER NOT NULL DEFAULT 0,
                reject INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY ("feed_id") REFERENCES "feeds" ("id")
                  ON UPDATE CASCADE
                  ON DELETE CASCADE,
                PRIMARY KEY ("id")
              );
            """
            )
        entries_table_sql = (
            """
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER NOT NULL,
                title TEXT NOT NULL,
                link TEXT NOT NULL,
                summary TEXT,
                enclosure TEXT,
                entry_id TEXT NOT NULL,
                feed_id INTEGER NOT NULL,
                timestamp TEXT,
                read INTEGER NOT NULL DEFAULT 0,
                reject INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY ("feed_id") REFERENCES "feeds" ("id")
                  ON UPDATE CASCADE
                  ON DELETE CASCADE,
                PRIMARY KEY ("id")
              );
            """
            )
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
        # TODO Rethink!
        # Albeit, probably, more expensive, we might want to have feed_id
        # as foreign key, as it is with feeds_properties and feeds_state
        feeds_categories_table_sql = (
            """
            CREATE TABLE IF NOT EXISTS feeds_categories (
                id INTEGER NOT NULL,
                category_id INTEGER NOT NULL UNIQUE,
                feed_id INTEGER,
                FOREIGN KEY ("category_id") REFERENCES "categories" ("id")
                  ON UPDATE CASCADE
                  ON DELETE CASCADE,
                PRIMARY KEY (id)
              );
            """
            )
        feeds_properties_table_sql = (
            """
            CREATE TABLE IF NOT EXISTS feeds_properties (
                id INTEGER NOT NULL,
                feed_id INTEGER NOT NULL UNIQUE,
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
        feeds_rules_table_sql = (
            """
            CREATE TABLE IF NOT EXISTS feeds_rules (
                id INTEGER NOT NULL,
                feed_id INTEGER NOT NULL UNIQUE,
                type TEXT NOT NULL,
                base TEXT NOT NULL,
                title TEXT NOT NULL,
                link TEXT NOT NULL,
                enclosure TEXT,
                summary TEXT,
                FOREIGN KEY ("feed_id") REFERENCES "feeds" ("id")
                  ON UPDATE CASCADE
                  ON DELETE CASCADE,
                PRIMARY KEY (id)
              );
            """
            )
        feeds_state_table_sql = (
            """
            CREATE TABLE IF NOT EXISTS feeds_state (
                id INTEGER NOT NULL,
                feed_id INTEGER NOT NULL UNIQUE,
                enabled INTEGER NOT NULL DEFAULT 1,
                updated TEXT,
                scanned TEXT,
                renewed TEXT,
                status_code INTEGER,
                valid INTEGER,
                filter INTEGER NOT NULL DEFAULT 1,
                priority INTEGER,
                FOREIGN KEY ("feed_id") REFERENCES "feeds" ("id")
                  ON UPDATE CASCADE
                  ON DELETE CASCADE,
                PRIMARY KEY ("id")
              );
            """
            )
        feeds_statistics_table_sql = (
            """
            CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER NOT NULL,
                feed_id INTEGER NOT NULL UNIQUE,
                offline INTEGER,
                entries INTEGER,
                entries INTEGER,
                FOREIGN KEY ("feed_id") REFERENCES "feeds" ("id")
                  ON UPDATE CASCADE
                  ON DELETE CASCADE,
                PRIMARY KEY ("id")
              );
            """
            )
        feeds_tags_table_sql = (
            """
            CREATE TABLE IF NOT EXISTS feeds_tags (
                id INTEGER NOT NULL,
                feed_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                FOREIGN KEY ("feed_id") REFERENCES "feeds" ("id")
                  ON UPDATE CASCADE
                  ON DELETE CASCADE,
                FOREIGN KEY ("tag_id") REFERENCES "tags" ("id")
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
        status_table_sql = (
            """
            CREATE TABLE IF NOT EXISTS status (
                id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value INTEGER,
                PRIMARY KEY ("id")
              );
            """
            )
        tags_table_sql = (
            """
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER NOT NULL,
                tag TEXT NOT NULL UNIQUE,
                PRIMARY KEY ("id")
              );
            """
            )
        cur = conn.cursor()
        # cur = get_cursor(db_file)
        cur.execute(archive_table_sql)
        cur.execute(entries_table_sql)
        cur.execute(feeds_table_sql)
        cur.execute(feeds_state_table_sql)
        cur.execute(feeds_properties_table_sql)
        cur.execute(feeds_rules_table_sql)
        cur.execute(feeds_tags_table_sql)
        cur.execute(filters_table_sql)
        # cur.execute(statistics_table_sql)
        cur.execute(settings_table_sql)
        cur.execute(status_table_sql)
        cur.execute(tags_table_sql)


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
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {}'
                .format(function_name, db_file))
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
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {}'
                .format(function_name, db_file))
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            for feed in feeds:
                logger.debug('{}: feed: {}'
                            .format(function_name, feed))
                url = feed[0]
                title = feed[1]
                sql = (
                    """
                    INSERT
                    INTO feeds(
                        name, url)
                    VALUES(
                        ?, ?)
                    """
                    )
                par = (
                    title, url
                    )
                try:
                    cur.execute(sql, par)
                except IntegrityError as e:
                    logger.warning("Skipping: " + str(url))
                    logger.error(e)


async def add_metadata(db_file):
    """
    Insert a new feed into the feeds table.

    Parameters
    ----------
    db_file : str
        Path to database file.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {}'
                .format(function_name, db_file))
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = (
                """
                SELECT id
                FROM feeds
                ORDER BY id ASC
                """
                )
            ixs = cur.execute(sql).fetchall()
            for ix in ixs:
                feed_id = ix[0]
                insert_feed_status(cur, feed_id)
                insert_feed_properties(cur, feed_id)


def insert_feed_status(cur, feed_id):
    """
    Set feed status.

    Parameters
    ----------
    cur : object
        Cursor object.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: feed_id: {}'
                .format(function_name, feed_id))
    sql = (
        """
        INSERT
        INTO feeds_state(
            feed_id)
        VALUES(
            ?)
        """
        )
    par = (feed_id,)
    try:
        cur.execute(sql, par)
    except IntegrityError as e:
        logger.warning(
            "Skipping feed_id {} for table feeds_state".format(feed_id))
        logger.error(e)


def insert_feed_properties(cur, feed_id):
    """
    Set feed properties.

    Parameters
    ----------
    cur : object
        Cursor object.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: feed_id: {}'
                .format(function_name, feed_id))
    sql = (
        """
        INSERT
        INTO feeds_properties(
            feed_id)
        VALUES(
            ?)
        """
        )
    par = (feed_id,)
    try:
        cur.execute(sql, par)
    except IntegrityError as e:
        logger.warning(
            "Skipping feed_id {} for table feeds_properties".format(feed_id))
        logger.error(e)


async def insert_feed(db_file, url, title=None, entries=None, version=None,
                      encoding=None, language=None, status_code=None,
                      updated=None):
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
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} url: {}'
                .format(function_name, db_file, url))
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = (
                """
                INSERT
                INTO feeds(
                    name, url)
                VALUES(
                    ?, ?)
                """
                )
            par = (
                title, url
                )
            cur.execute(sql, par)
            sql = (
                """
                SELECT id
                FROM feeds
                WHERE url = :url
                """
                )
            par = (url,)
            feed_id = cur.execute(sql, par).fetchone()[0]
            sql = (
                """
                INSERT
                INTO feeds_state(
                    feed_id, enabled, updated, status_code, valid)
                VALUES(
                    ?, ?, ?, ?, ?)
                """
                )
            par = (
                feed_id, 1, updated, status_code, 1
                )
            cur.execute(sql, par)
            sql = (
                """
                INSERT
                INTO feeds_properties(
                    feed_id, entries, type, encoding, language)
                VALUES(
                    ?, ?, ?, ?, ?)
                """
                )
            par = (
                feed_id, entries, version, encoding, language
                )
            cur.execute(sql, par)


async def insert_feed_(db_file, url, title=None, entries=None, version=None,
                       encoding=None, language=None, status_code=None,
                       updated=None):
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
    status : str, optional
        HTTP status code. The default is None.
    updated : ???, optional
        Date feed was last updated. The default is None.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} url: {}'
                .format(function_name, db_file, url))
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = (
                """
                INSERT
                INTO feeds(
                    name, url)
                VALUES(
                    ?, ?)
                """
                )
            par = (
                title, url
                )
            cur.execute(sql, par)
            sql = (
                """
                SELECT id
                FROM feeds
                WHERE url = :url
                """
                )
            par = (url,)
            feed_id = cur.execute(sql, par).fetchone()[0]
            insert_feed_properties(
                cur, feed_id, entries=None, 
                version=None, encoding=None, language=None)
            insert_feed_status(
                cur, feed_id, status_code=None, updated=None)


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
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} url: {}'
                .format(function_name, db_file, url))
    with create_connection(db_file) as conn:
        async with DBLOCK:
            cur = conn.cursor()
            sql = (
                """
                DELETE
                FROM feeds
                WHERE url = ?
                """
                )
            par = (url,)
            cur.execute(sql, par)


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
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} ix: {}'
                .format(function_name, db_file, ix))
    with create_connection(db_file) as conn:
        async with DBLOCK:
            cur = conn.cursor()
            # # NOTE Should we move DBLOCK to this line? 2022-12-23
            # sql = (
            #     "DELETE "
            #     "FROM entries "
            #     "WHERE feed_id = ?"
            #     )
            # par = (url,)
            # cur.execute(sql, par) # Error? 2024-01-05
            # sql = (
            #     "DELETE "
            #     "FROM archive "
            #     "WHERE feed_id = ?"
            #     )
            # par = (url,)
            # cur.execute(sql, par)
            sql = (
                """
                DELETE
                FROM feeds
                WHERE id = ?
                """
                )
            par = (ix,)
            cur.execute(sql, par)


def get_feeds_by_tag_id(db_file, tag_id):
    """
    Get feeds of given tag.

    Parameters
    ----------
    db_file : str
        Path to database file.
    tag_id : str
        Tag ID.

    Returns
    -------
    result : tuple
        List of tags.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} tag_id: {}'
                .format(function_name, db_file, tag_id))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT feeds.*
            FROM feeds
            INNER JOIN feeds_tags ON feeds.id = feeds_tags.feed_id
            INNER JOIN tags ON tags.id = feeds_tags.tag_id
            WHERE tags.id = ?;
            """
            )
        par = (tag_id,)
        result = cur.execute(sql, par).fetchall()
        return result


def get_tags_by_feed_id(db_file, feed_id):
    """
    Get tags of given feed.

    Parameters
    ----------
    db_file : str
        Path to database file.
    feed_id : str
        Feed ID.

    Returns
    -------
    result : tuple
        List of tags.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} feed_id: {}'
                .format(function_name, db_file, feed_id))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT tags.tag
            FROM tags
            INNER JOIN feeds_tags ON tags.id = feeds_tags.tag_id
            INNER JOIN feeds ON feeds.id = feeds_tags.feed_id
            WHERE feeds.id = ?;
            """
            )
        par = (feed_id,)
        result = cur.execute(sql, par).fetchall()
        return result


async def set_feed_id_and_tag_id(db_file, feed_id, tag_id):
    """
    Set Feed ID and Tag ID.

    Parameters
    ----------
    db_file : str
        Path to database file.
    feed_id : str
        Feed ID
    tag_id : str
        Tag ID
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} feed_id: {} tag_id: {}'
                .format(function_name, db_file, feed_id, tag_id))
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = (
                """
                INSERT
                INTO feeds_tags(
                    feed_id, tag_id)
                VALUES(
                    :feed_id, :tag_id)
                """
                )
            par = {
                "feed_id": feed_id,
                "tag_id": tag_id
                }
            cur.execute(sql, par)


def get_tag_id(db_file, tag_name):
    """
    Get ID of given tag. Check whether tag exist.

    Parameters
    ----------
    db_file : str
        Path to database file.
    tag_name : str
        Tag name.

    Returns
    -------
    ix : str
        Tag ID.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} tag_name: {}'
                .format(function_name, db_file, tag_name))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT id
            FROM tags
            WHERE tag = ?
            """
            )
        par = (tag_name,)
        ix = cur.execute(sql, par).fetchone()
    return ix


def get_tag_name(db_file, ix):
    """
    Get name of given tag. Check whether tag exist.

    Parameters
    ----------
    db_file : str
        Path to database file.
    ix : str
        Tag ID.

    Returns
    -------
    tag_name : str
        Tag name.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} ix: {}'
                .format(function_name, db_file, ix))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT tag
            FROM tags
            WHERE id = ?
            """
            )
        par = (ix,)
        tag_name = cur.execute(sql, par).fetchone()
    return tag_name


def is_tag_id_associated(db_file, tag_id):
    """
    Check whether tag_id is associated with any feed.

    Parameters
    ----------
    db_file : str
        Path to database file.
    tag_id : str
        Tag ID.

    Returns
    -------
    tag_id : str
        Tag ID.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} tag_id: {}'
                .format(function_name, db_file, tag_id))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT tag_id
            FROM feeds_tags
            WHERE tag_id = :tag_id
            """
            )
        par = {
            "tag_id": tag_id
            }
        tag_id = cur.execute(sql, par).fetchone()
    return tag_id


async def delete_tag_by_index(db_file, ix):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} ix: {}'
                .format(function_name, db_file, ix))
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = (
                """
                DELETE
                FROM tags
                WHERE id = :id
                """
                )
            par = {
                "id": ix
                }
            cur.execute(sql, par)


def is_tag_id_of_feed_id(db_file, tag_id, feed_id):
    """
    Check whether given tag is related with given feed.

    Parameters
    ----------
    db_file : str
        Path to database file.
    feed_id : str
        Feed ID.
    tag_id : str
        Tag ID.

    Returns
    -------
    tag_id : str
        Tag ID.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} tag_id: {} feed_id: {}'
                .format(function_name, db_file, feed_id, tag_id))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT tag_id
            FROM feeds_tags
            WHERE tag_id = :tag_id AND feed_id = :feed_id
            """
            )
        par = {
            "tag_id": tag_id,
            "feed_id": feed_id
            }
        tag_id = cur.execute(sql, par).fetchone()
    return tag_id


async def delete_feed_id_tag_id(db_file, feed_id, tag_id):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} tag_id: {} feed_id: {}'
                .format(function_name, db_file, feed_id, tag_id))
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = (
                """
                DELETE
                FROM feeds_tags
                WHERE tag_id = :tag_id AND feed_id = :feed_id
                """
                )
            par = {
                "tag_id": tag_id,
                "feed_id": feed_id
                }
            cur.execute(sql, par)


async def set_new_tag(db_file, tag):
    """
    Set new Tag

    Parameters
    ----------
    db_file : str
        Path to database file.
    tag : str
        Tag
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} tag: {}'
                .format(function_name, db_file, tag))
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = (
                """
                INSERT
                INTO tags(
                    tag)
                VALUES(
                    :tag)
                """
                )
            par = {
                "tag": tag
                }
            cur.execute(sql, par)


def get_feed_id_and_name(db_file, url):
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
    result : tuple
        List of ID and Name of feed.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} url: {}'
                .format(function_name, db_file, url))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT id, name
            FROM feeds
            WHERE url = ?
            """
            )
        par = (url,)
        result = cur.execute(sql, par).fetchone()
        return result


def get_number_of_items(db_file, table):
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
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} table: {}'
                .format(function_name, db_file, table))
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


def get_number_of_feeds_active(db_file):
    """
    Return number of active feeds.

    Parameters
    ----------
    db_file : str
        Path to database file.

    Returns
    -------
    count : str
        Number of rows.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {}'
                .format(function_name, db_file))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT count(id)
            FROM feeds_state
            WHERE enabled = 1
            """
            )
        count = cur.execute(sql).fetchone()[0]
        return count


def get_number_of_entries_unread(db_file):
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
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {}'
                .format(function_name, db_file))
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


def get_entries(db_file, num):
    """
    Extract information from entries.

    Parameters
    ----------
    db_file : str
        Path to database file.
    num : str, optional
        Number. The default is None.

    Returns
    -------
    result : tuple
        News items.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} num: {}'
                .format(function_name, db_file, num))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT id, title, link, summary, enclosure, feed_id, timestamp
            FROM entries
            UNION ALL
            SELECT id, title, link, summary, enclosure, feed_id, timestamp
            FROM archive
            ORDER BY timestamp DESC
            LIMIT :num
            """
            )
        par = (num,)
        result = cur.execute(sql, par).fetchall()
        return result


def get_entries_rejected(db_file, num):
    """
    Extract information from rejected entries.

    Parameters
    ----------
    db_file : str
        Path to database file.
    num : str, optional
        Number. The default is None.

    Returns
    -------
    result : tuple
        News items.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} num: {}'
                .format(function_name, db_file, num))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT id, title, link, summary, enclosure, feed_id, timestamp
            FROM entries
            WHERE reject = 1
            UNION ALL
            SELECT id, title, link, summary, enclosure, feed_id, timestamp
            FROM archive
            WHERE reject = 1
            ORDER BY timestamp DESC
            LIMIT :num
            """
            )
        par = (num,)
        result = cur.execute(sql, par).fetchall()
        return result


def get_unread_entries(db_file, num):
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
    result : tuple
        News items.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} num: {}'
                .format(function_name, db_file, num))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT id, title, link, summary, enclosure, feed_id, timestamp
            FROM entries
            WHERE read = 0
            UNION ALL
            SELECT id, title, link, summary, enclosure, feed_id, timestamp
            FROM archive
            ORDER BY timestamp DESC
            LIMIT :num
            """
            )
        par = (num,)
        result = cur.execute(sql, par).fetchall()
        return result


def get_feed_id_by_entry_index(db_file, ix):
    """
    Get feed id by entry index.

    Parameters
    ----------
    db_file : str
        Path to database file.
    ix : str
        Index.

    Returns
    -------
    feed_id : str
        Feed index.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} ix: {}'
                .format(function_name, db_file, ix))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT feed_id
            FROM entries
            WHERE id = :ix
            """
            )
        par = (ix,)
        feed_id = cur.execute(sql, par).fetchone()
        return feed_id


def get_feed_id(db_file, url):
    """
    Get index of given feed.

    Parameters
    ----------
    db_file : str
        Path to database file.
    url : str
        URL.

    Returns
    -------
    feed_id : str
        Feed index.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} url: {}'
                .format(function_name, db_file, url))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT id
            FROM feeds
            WHERE url = :url
            """
            )
        par = (url,)
        feed_id = cur.execute(sql, par).fetchone()
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
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: ix: {}'
                .format(function_name, ix))
    sql = (
        """
        UPDATE entries
        SET read = 1
        WHERE id = ?
        """
        )
    par = (ix,)
    cur.execute(sql, par)


def get_number_of_unread_entries_by_feed(db_file, feed_id):
    """
    Count entries of given feed.

    Parameters
    ----------
    db_file : str
        Path to database file.
    feed_id : str
        Feed Id.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} feed_id: {}'
                .format(function_name, db_file, feed_id))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT count(id)
            FROM entries
            WHERE read = 0 AND feed_id = ?
            """
            )
        par = (feed_id,)
        count = cur.execute(sql, par).fetchone()
        return count


async def mark_feed_as_read(db_file, feed_id):
    """
    Set read status of entries of given feed as read.

    Parameters
    ----------
    db_file : str
        Path to database file.
    feed_id : str
        Feed Id.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} feed_id: {}'
                .format(function_name, db_file, feed_id))
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
            par = (feed_id,)
            cur.execute(sql, par)


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
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} ix: {}'
                .format(function_name, db_file, ix))
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
            par = (ix,)
            cur.execute(sql, par)


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
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} ix: {}'
                .format(function_name, db_file, ix))
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
            par = (ix,)
            try:
                cur.execute(sql, par)
            except Exception as e:
                print('ERROR DB insert from entries into archive at index {} '
                      'for {}. Reason: {}'.format(ix, db_file, e))
            sql = (
                """
                DELETE
                FROM entries
                WHERE id = :ix
                """
                )
            par = (ix,)
            try:
                cur.execute(sql, par)
            except:
                print('ERROR DB deleting items from table entries at index {} '
                      'for DB {}', ix, db_file)


def get_feed_title(db_file, ix):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} ix: {}'
                .format(function_name, db_file, ix))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT name
            FROM feeds
            WHERE id = :ix
            """
            )
        par = (ix,)
        title = cur.execute(sql, par).fetchone()
        return title


async def set_feed_title(db_file, feed_id, name):
    """
    Set new name for feed.

    Parameters
    ----------
    db_file : str
        Path to database file.
    feed_id : str
        Index of feed.
    name : str
        New name.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} feed_id: {} name: {}'
                .format(function_name, db_file, feed_id, name))
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = (
                """
                UPDATE feeds
                SET name = :name
                WHERE id = :feed_id
                """
                )
            par = {
                "name": name,
                "feed_id": feed_id
                }
            cur.execute(sql, par)


def get_entry_title(db_file, ix):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} ix: {}'
                .format(function_name, db_file, ix))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = ( # TODO Handletable archive too
            """
            SELECT title
            FROM entries
            WHERE id = :ix
            """
            )
        par = (ix,)
        title = cur.execute(sql, par).fetchone()
        return title


def get_entry_url(db_file, ix):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} ix: {}'
                .format(function_name, db_file, ix))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = ( # TODO Handletable archive too
            """
            SELECT link
            FROM entries
            WHERE id = :ix
            """
            )
        par = (ix,)
        url = cur.execute(sql, par).fetchone()
        return url


def get_feed_url(db_file, ix):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} ix: {}'
                .format(function_name, db_file, ix))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT url
            FROM feeds
            WHERE id = :ix
            """
            )
        par = (ix,)
        url = cur.execute(sql, par).fetchone()
        return url


async def mark_as_read(db_file, ix):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} ix: {}'
                .format(function_name, db_file, ix))
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
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {}'
                .format(function_name, db_file))
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
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: ix: {}'
                .format(function_name, ix))
    sql = (
        """
        DELETE
        FROM archive
        WHERE id = ?
        """
        )
    par = (ix,)
    cur.execute(sql, par)


async def update_statistics(cur):
    """
    Update table statistics.

    Parameters
    ----------
    cur : object
        Cursor object.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}'.format(function_name))
    stat_dict = {}
    stat_dict["feeds"] = get_number_of_items(cur, 'feeds')
    stat_dict["entries"] = get_number_of_items(cur, 'entries')
    stat_dict["unread"] = get_number_of_entries_unread(cur=cur)
    for i in stat_dict:
        sql = (
            "SELECT id "
            "FROM statistics "
            "WHERE title = ?"
            )
        par = (i,)
        cur.execute(sql, par)
        if cur.fetchone():
            sql = (
                "UPDATE statistics "
                "SET number = :num "
                "WHERE title = :title"
                )
            par = {
                "title": i,
                "num": stat_dict[i]
                }
            cur.execute(sql, par)
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
            par = (ix, i, stat_dict[i])
            cur.execute(sql, par)


async def set_enabled_status(db_file, feed_id, status):
    """
    Set status of feed to enabled or not enabled (i.e. disabled).

    Parameters
    ----------
    db_file : str
        Path to database file.
    feed_id : str
        Index of feed.
    status : int
        0 or 1.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} feed_id: {} status: {}'
                .format(function_name, db_file, feed_id, status))
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = (
                """
                UPDATE feeds_state
                SET enabled = :status
                WHERE feed_id = :feed_id
                """
                )
            par = {
                "status": status,
                "feed_id": feed_id
                }
            cur.execute(sql, par)


"""
TODO

Investigate what causes date to be int 0

NOTE

When time functions of slixfeed.timedate
were async, there were errors of coroutines

"""
async def add_entry(db_file, title, link, entry_id, feed_id, date,
                    read_status):
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
    feed_id : str
        Feed Id.
    date : str
        Date.
    read_status : str
        0 or 1.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} title: {} link: {} entry_id: {} feed_id: {} date: {} read_status: {}'
                .format(function_name, db_file, title, link, entry_id, feed_id, date, read_status))
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = (
                """
                INSERT
                INTO entries(
                    title, link, entry_id, feed_id, timestamp, read)
                VALUES(
                    :title, :link, :entry_id, :feed_id, :timestamp, :read)
                """
                )
            par = {
                "title": title,
                "link": link,
                "entry_id": entry_id,
                "feed_id": feed_id,
                "timestamp": date,
                "read": read_status
                }
            cur.execute(sql, par)
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


async def add_entries_and_update_timestamp(db_file, feed_id, new_entries):
    """
    Add new entries.

    Parameters
    ----------
    db_file : str
        Path to database file.
    new_entries : tuple
        Set of entries as dict.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} feed_id: {}'
                .format(function_name, db_file, feed_id))
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            for entry in new_entries:
                logger.debug('{}: db_file: {} feed_id: {} entry: {}'
                            .format(function_name, db_file, feed_id, entry["title"]))
                sql = (
                    """
                    INSERT
                    INTO entries(
                        title, link, summary, enclosure, entry_id, feed_id, timestamp, read)
                    VALUES(
                        :title, :link, :summary, :enclosure, :entry_id, :feed_id, :timestamp, :read)
                    """
                    )
                par = {
                    "title": entry["title"],
                    "link": entry["link"],
                    "summary": entry["summary"],
                    "enclosure": entry["enclosure"],
                    "entry_id": entry["entry_id"],
                    "feed_id": feed_id,
                    "timestamp": entry["date"],
                    "read": entry["read_status"]
                    }
                cur.execute(sql, par)
            sql = (
                """
                UPDATE feeds_state
                SET renewed = :renewed
                WHERE feed_id = :feed_id
                """
                )
            par = {
                "renewed": time.time(),
                "feed_id": feed_id
                }
            cur.execute(sql, par)


async def set_date(db_file, feed_id):
    """
    Set renewed date of given feed.

    Parameters
    ----------
    db_file : str
        Path to database file.
    feed_id : str
        Feed Id.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} feed_id: {}'
                .format(function_name, db_file, feed_id))
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = (
                """
                UPDATE feeds_state
                SET renewed = :renewed
                WHERE feed_id = :feed_id
                """
                )
            par = {
                "renewed": time.time(),
                "feed_id": feed_id
                }
            # cur = conn.cursor()
            cur.execute(sql, par)


async def update_feed_status(db_file, feed_id, status_code):
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
    function_name = sys._getframe().f_code.co_name
    print('{}: db_file: {} feed_id: {} status_code: {}'
                .format(function_name, db_file, feed_id, status_code))
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = (
                """
                UPDATE feeds_state
                SET status_code = :status_code, scanned = :scanned
                WHERE feed_id = :feed_id
                """
                )
            par = {
                "status_code": status_code,
                "scanned": time.time(),
                "feed_id": feed_id
                }
            cur.execute(sql, par)


async def update_feed_validity(db_file, feed_id, valid):
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
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} feed_id: {} valid: {}'
                .format(function_name, db_file, feed_id, valid))
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = (
                """
                UPDATE feeds_state
                SET valid = :valid
                WHERE feed_id = :feed_id
                """
                )
            par = {
                "valid": valid,
                "feed_id": feed_id
                }
            cur.execute(sql, par)


async def update_feed_properties(db_file, feed_id, entries, updated):
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
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} feed_id: {} entries: {} updated: {}'
                .format(function_name, db_file, feed_id, entries, updated))
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = (
                """
                UPDATE feeds_properties
                SET entries = :entries
                WHERE feed_id = :feed_id
                """
                )
            par = {
                "entries"  : entries,
                "feed_id": feed_id
                }
            cur.execute(sql, par)


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
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} limit: {}'
                .format(function_name, db_file, limit))
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
                    DELETE
                    FROM archive
                    WHERE id
                    IN (
                        SELECT id
                        FROM archive
                        ORDER BY timestamp ASC
                        LIMIT :difference
                        )
                    """
                    )
                par = {
                    "difference": difference
                    }
                cur.execute(sql, par)


# TODO Move entries that don't exist into table archive.
# NOTE Entries that are read from archive are deleted.
# NOTE Unlike entries from table entries, entries from
#      table archive are not marked as read.
def get_entries_of_feed(db_file, feed_id):
    """
    Get entries of given feed.

    Parameters
    ----------
    db_file : str
        Path to database file.
    feed_id : str
        Feed Id.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{} db_file: {} feed_id: {}'
                .format(function_name, db_file, feed_id))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT id, title, link, entry_id, timestamp, read
            FROM entries
            WHERE feed_id = ?
            ORDER BY timestamp DESC
            """
            )
        par = (feed_id,)
        items = cur.execute(sql, par).fetchall()
        return items


# TODO What is this function for? 2024-01-02
# def get_feeds(db_file):
#     """
#     Query table feeds for Title, URL, Categories, Tags.

#     Parameters
#     ----------
#     db_file : str
#         Path to database file.

#     Returns
#     -------
#     result : tuple
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
def get_feeds_url(db_file):
    """
    Query table feeds for URLs.

    Parameters
    ----------
    db_file : str
        Path to database file.

    Returns
    -------
    result : tuple
        URLs of active feeds.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{} db_file: {}'
                .format(function_name, db_file))
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


def get_feeds_by_enabled_state(db_file, enabled_state):
    """
    Query table feeds by enabled state.

    Parameters
    ----------
    db_file : str
        Path to database file.
    enabled_state : boolean
        False or True.

    Returns
    -------
    result : tuple
        List of URLs.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} enabled_state: {}'
                .format(function_name, db_file, enabled_state))
    if enabled_state:
        enabled_state = 1
    else:
        enabled_state = 0
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT feeds.*
            FROM feeds
            INNER JOIN feeds_state ON feeds.id = feeds_state.feed_id
            WHERE feeds_state.enabled = ?
            """
            )
        par = (enabled_state,)
        result = cur.execute(sql, par).fetchall()
        return result


def get_active_feeds_url(db_file):
    """
    Query table feeds for active URLs.

    Parameters
    ----------
    db_file : str
        Path to database file.

    Returns
    -------
    result : tuple
        URLs of active feeds.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {}'
                .format(function_name, db_file))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT feeds.url
            FROM feeds
            INNER JOIN feeds_state ON feeds.id = feeds_state.feed_id
            WHERE feeds_state.enabled = 1
            """
            )
        result = cur.execute(sql).fetchall()
        return result


def get_tags(db_file):
    """
    Query table tags and list items.

    Parameters
    ----------
    db_file : str
        Path to database file.

    Returns
    -------
    result : tuple
        List of tags.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {}'
                .format(function_name, db_file))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT tag, id
            FROM tags
            """
            )
        result = cur.execute(sql).fetchall()
        return result


def get_feeds(db_file):
    """
    Query table feeds and list items.

    Parameters
    ----------
    db_file : str
        Path to database file.

    Returns
    -------
    result : tuple
        URLs of feeds.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {}'
                .format(function_name, db_file))
    # TODO
    # 1) Select id from table feeds
    #    Select name, url (feeds) updated, enabled, feed_id (status)
    # 2) Sort feeds by id. Sort status by feed_id
    # result += cur.execute(sql).fetchall()
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT id, name, url
            FROM feeds
            """
            )
        result = cur.execute(sql).fetchall()
        return result


def get_last_entries(db_file, num):
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
    titles_list : tuple
        List of recent N entries as message.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} num: {}'
                .format(function_name, db_file, num))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
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
        par = (num,)
        result = cur.execute(sql, par).fetchall()
        return result


def search_feeds(db_file, query):
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
    result : tuple
        Feeds of specified keywords as message.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} query: {}'
                .format(function_name, db_file, query))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT name, id, url
            FROM feeds
            WHERE name LIKE ?
            OR url LIKE ?
            LIMIT 50
            """
            )
        par = [f'%{query}%', f'%{query}%']
        result = cur.execute(sql, par).fetchall()
        return result


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
    titles_list : tuple
        Entries of specified keywords as message.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} query: {}'
                .format(function_name, db_file, query))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
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
        par = (f'%{query}%', f'%{query}%')
        result = cur.execute(sql, par).fetchall()
        return result


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
def check_entry_exist(db_file, feed_id, entry_id=None, title=None, link=None,
                      date=None):
    """
    Check whether an entry exists.
    If entry has an ID, check by ID.
    If entry has timestamp, check by title, link and date.
    Otherwise, check by title and link.

    Parameters
    ----------
    db_file : str
        Path to database file.
    feed_id : str
        Feed Id.
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
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} feed_id: {}'
                .format(function_name, db_file, feed_id))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        exist = False
        if entry_id:
            sql = (
                """
                SELECT id
                FROM entries
                WHERE entry_id = :entry_id and feed_id = :feed_id
                """
                )
            par = {
                "entry_id": entry_id,
                "feed_id": feed_id
                }
            result = cur.execute(sql, par).fetchone()
            if result: exist = True
        elif date:
            sql = (
                """
                SELECT id
                FROM entries
                WHERE title = :title AND link = :link AND timestamp = :date
                """
                )
            par = {
                "title": title,
                "link": link,
                "date": date
                }
            try:
                result = cur.execute(sql, par).fetchone()
                if result: exist = True
            except:
                logger.error("source =", feed_id)
                logger.error("date =", date)
        else:
            sql = (
                """
                SELECT id
                FROM entries
                WHERE title = :title AND link = :link
                """
                )
            par = {
                "title": title,
                "link": link
                }
            result = cur.execute(sql, par).fetchone()
            if result: exist = True
        # try:
        #     if result:
        #         return True
        #     else:
        #         return None
        # except:
        #     print(current_time(), "ERROR DATE: result =", url)
        return exist


async def set_setting_value(db_file, key_value):
    """
    Set setting value.

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
    key = key_value[0]
    val = key_value[1]

    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} key: {} val: {}'
                .format(function_name, db_file, key, val))

    if not val:
        raise Exception('Missing value for key "{}" ({}).'.format(key, db_file))
        # logger.error('Missing value for key "{}" ({}).'.format(key, db_file))
        # return

    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = (
                """
                INSERT
                INTO settings(
                    key, value)
                VALUES(
                    :key, :val)
                """
                )
            par = {
                "key": key,
                "val": val
                }
            cur.execute(sql, par)


async def update_setting_value(db_file, key_value):
    """
    Update setting value.

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
    val = key_value[1]

    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} key: {} val: {}'
                .format(function_name, db_file, key, val))

    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = (
                """
                UPDATE settings
                SET value = :val
                WHERE key = :key
                """
                )
            par = {
                "key": key,
                "val": val
                }
            cur.execute(sql, par)
            # except:
            #     logging.debug(
            #         "No specific value set for key {}.".format(key)
            #         )


async def delete_filter(db_file, key):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} key: {}'
                .format(function_name, db_file, key))
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = (
                """
                DELETE
                FROM filters
                WHERE key = ?
                """
                )
            par = (key,)
            cur.execute(sql, par)


async def delete_setting(db_file, key):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} key: {}'
                .format(function_name, db_file, key))
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = (
                """
                DELETE
                FROM settings
                WHERE key = ?
                """
                )
            par = (key,)
            cur.execute(sql, par)


async def delete_settings(db_file):
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {}'
                .format(function_name, db_file))
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = (
                """
                DELETE
                FROM settings
                """
                )
            cur.execute(sql)


def get_setting_value(db_file, key):
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
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} key: {}'
                .format(function_name, db_file, key))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT value
            FROM settings
            WHERE key = ?
            """
            )
        par = (key,)
        value = cur.execute(sql, par).fetchone()
        return value


def is_setting_key(db_file, key):
    """
    Check whether setting key exist.

    Parameters
    ----------
    db_file : str
        Path to database file.
    key : str
        Key: allow, deny.

    Returns
    -------
    key : str
        Key.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} key: {}'
                .format(function_name, db_file, key))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT key
            FROM settings
            WHERE key = ?
            """
            )
        par = (key,)
        key = cur.execute(sql, par).fetchone()
    return key


async def set_filter_value(db_file, key_value):
    """
    Set settings value.

    Parameters
    ----------
    db_file : str
        Path to database file.
    key_value : list
         key : str
               allow, deny, replace.
         value : int
               Numeric value.
    """
    key = key_value[0]
    val = key_value[1]

    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} key: {} val: {}'
                .format(function_name, db_file, key, val))

    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = (
                """
                INSERT
                INTO filters(
                    key, value)
                VALUES(
                    :key, :val)
                """
                )
            par = {
                "key": key,
                "val": val
                }
            cur.execute(sql, par)


async def update_filter_value(db_file, key_value):
    """
    Update settings value.

    Parameters
    ----------
    db_file : str
        Path to database file.
    key_value : list
         key : str
               allow, deny, replace.
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

    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} key: {} val: {}'
                .format(function_name, db_file, key, val))

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
            par = {
                "key": key,
                "value": val
                }
            cur.execute(sql, par)


def is_filter_key(db_file, key):
    """
    Check whether filter key exist.

    Parameters
    ----------
    db_file : str
        Path to database file.
    key : str
        Key: allow, deny.

    Returns
    -------
    key : str
        Key.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} key: {}'
                .format(function_name, db_file, key))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT key
            FROM filters
            WHERE key = ?
            """
            )
        par = (key,)
        key = cur.execute(sql, par).fetchone()
        return key


def get_filter_value(db_file, key):
    """
    Get filter value.

    Parameters
    ----------
    db_file : str
        Path to database file.
    key : str
        Key: allow, deny.

    Returns
    -------
    value : str
        List of strings.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} key: {}'
                .format(function_name, db_file, key))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT value
            FROM filters
            WHERE key = ?
            """
            )
        par = (key,)
        value = cur.execute(sql, par).fetchone()
    return value


async def set_last_update_time(db_file):
    """
    Set value of last_update.

    Parameters
    ----------
    db_file : str
        Path to database file.

    Returns
    -------
    None.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {}'
                .format(function_name, db_file))
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = (
                """
                INSERT
                INTO status(
                    key, value)
                VALUES(
                    :key, :value)
                """
                )
            par = {
                "key": "last_update",
                "value": time.time()
                }
            cur.execute(sql, par)


def get_last_update_time(db_file):
    """
    Get value of last_update.

    Parameters
    ----------
    db_file : str
        Path to database file.

    Returns
    -------
    val : str
        Time.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {}'
                .format(function_name, db_file))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        try:
            sql = (
                """
                SELECT value
                FROM status
                WHERE key = "last_update"
                """
                )
            value = cur.execute(sql).fetchone()[0]
            value = str(value)
        except:
            value = None
            logger.debug(
                "No specific value set for key last_update.")
    return value


async def update_last_update_time(db_file):
    """
    Update value of last_update.

    Parameters
    ----------
    db_file : str
        Path to database file.

    Returns
    -------
    None.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {}'
                .format(function_name, db_file))
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = (
                """
                UPDATE status
                SET value = :value
                WHERE key = "last_update"
                """
                )
            par = {
                "value": time.time()
                }
            cur.execute(sql, par)

########################################

######### EXPERIMENTAL TABLE ###########

########################################

def get_categories(db_file):
    """
    Get list of categories.

    Parameters
    ----------
    db_file : tuple
        Path to database file.

    Returns
    -------
    categories : str
        List of categories.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {}'
                .format(function_name, db_file))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT DISTINCT category
            FROM entries
            ORDER BY category ASC
            """
            )
        categories = cur.execute(sql).fetchall()
    return categories


def get_locales(db_file):
    """
    Get list of locales.

    Parameters
    ----------
    db_file : str
        Path to database file.

    Returns
    -------
    locales : tuple
        List of locales.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {}'
                .format(function_name, db_file))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT DISTINCT locale
            FROM entries
            ORDER BY locale ASC
            """
            )
        locales = cur.execute(sql).fetchall()
    return locales


def get_nations(db_file):
    """
    Get list of nations.

    Parameters
    ----------
    db_file : str
        Path to database file.

    Returns
    -------
    nations : tuple
        List of nations.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {}'
                .format(function_name, db_file))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT DISTINCT nation
            FROM entries
            ORDER BY nation ASC
            """
            )
        locales = cur.execute(sql).fetchall()
    return locales


# def get_tags(db_file):
#     """
#     Get list of title and urls.

#     Parameters
#     ----------
#     db_file : str
#         Path to database file.

#     Returns
#     -------
#     titles_urls : tuple
#         List of titles and urls.
#     """
#     with create_connection(db_file) as conn:
#         cur = conn.cursor()
#         sql = (
#             """
#             SELECT tags
#             FROM entries
#             ORDER BY tags ASC
#             """
#             )
#         titles_urls = cur.execute(sql).fetchall()
#     return titles_urls


def get_titles_tags_urls(db_file):
    """
    Get list of title and urls.

    Parameters
    ----------
    db_file : str
        Path to database file.

    Returns
    -------
    titles_urls : tuple
        List of titles and urls.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {}'
                .format(function_name, db_file))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT title, tags, url
            FROM entries
            ORDER BY title ASC
            LIMIT 800
            """
            )
        titles_tags_urls = cur.execute(sql).fetchall()
    return titles_tags_urls


def get_titles_tags_urls_by_category(db_file, category):
    """
    Get list of title and urls of given category.

    Parameters
    ----------
    db_file : str
        Path to database file.

    Returns
    -------
    titles_urls : tuple
        List of titles and urls.
    """
    function_name = sys._getframe().f_code.co_name
    logger.debug('{}: db_file: {} category: {}'
                .format(function_name, db_file, category))
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = (
            """
            SELECT title, tags, url
            FROM entries
            WHERE category = :category
            ORDER BY title ASC
            """
            )
        par = {
            "category": category
            }
        titles_tags_urls = cur.execute(sql, par).fetchall()
    return titles_tags_urls
