#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from sqlite3 import Error

import asyncio

from datetime import date
import feedparser

from eliot import start_action, to_file

# aiosqlite
DBLOCK = asyncio.Lock()

CURSORS = {}

def create_connection(db_file):
    # print("create_connection")
    # print("db_file")
    # print(db_file)
    # time.sleep(1)
    """
    Create a database connection to the SQLite database
    specified by db_file
    :param db_file: database file
    :return: Connection object or None
    """
    with start_action(action_type="create_connection()", db=db_file):
        conn = None
        try:
            conn = sqlite3.connect(db_file)
            return conn
        except Error as e:
            print(e)
        return conn


def create_tables(db_file):
    # print("create_tables")
    # print("db_file")
    # print(db_file)
    # time.sleep(1)
    with start_action(action_type="create_tables()", db=db_file):
        with create_connection(db_file) as conn:
            feeds_table_sql = """
                CREATE TABLE IF NOT EXISTS feeds (
                    id integer PRIMARY KEY,
                    name text,
                    address text NOT NULL,
                    enabled integer NOT NULL,
                    scanned text,
                    updated text,
                    status integer,
                    valid integer
                ); """
            entries_table_sql = """
                CREATE TABLE IF NOT EXISTS entries (
                    id integer PRIMARY KEY,
                    title text NOT NULL,
                    summary text NOT NULL,
                    link text NOT NULL,
                    source text,
                    read integer
                ); """
        
            c = conn.cursor()
            # c = get_cursor(db_file)
            c.execute(feeds_table_sql)
            c.execute(entries_table_sql)


def get_cursor(db_file):
    """
    Allocate a cursor to connection per database.
    :param db_file: database file
    :return: Cursor
    """
    with start_action(action_type="get_cursor()", db=db_file):
        if db_file in CURSORS:
            return CURSORS[db_file]
        else:
            with create_connection(db_file) as conn:
                cur = conn.cursor()
                CURSORS[db_file] = cur
        return CURSORS[db_file]


async def add_feed(db_file, url, res):
    # print("add_feed")
    # print("db_file")
    # print(db_file)
    # time.sleep(1)
    """
    Add a new feed into the feeds table
    :param conn:
    :param feed:
    :return: string
    """
    with start_action(action_type="add_feed()", url=url):
        #TODO consider async with DBLOCK
        #conn = create_connection(db_file)

        # with create_connection(db_file) as conn:
        #     #exist = await check_feed(conn, url)
        #     exist = await check_feed(db_file, url)
    
        # if not exist:
        #     res = await main.download_feed(url)
        # else:
        #     return "News source is already listed in the subscription list"
    
        async with DBLOCK:
            with create_connection(db_file) as conn:
                cur = conn.cursor()
                if res[0]:
                    feed = feedparser.parse(res[0])
                    if feed.bozo:
                        feed = (url, 1, res[1], 0)
                        #sql = """INSERT INTO feeds(address,enabled,status,valid)
                        #         VALUES(?,?,?,?) """
                        #cur.execute(sql, feed)
                        bozo = ("WARNING: Bozo detected. Failed to load URL.")
                        print(bozo)
                        return "Failed to parse URL as feed"
                    else:
                        title = feed["feed"]["title"]
                        feed = (title, url, 1, res[1], 1)
                        sql = """INSERT INTO feeds(name,address,enabled,status,valid)
                                 VALUES(?,?,?,?,?) """
                        cur.execute(sql, feed)
                else:
                    feed = (url, 1, res[1], 0)
                    #sql = "INSERT INTO feeds(address,enabled,status,valid) VALUES(?,?,?,?) "
                    #cur.execute(sql, feed)
                    return "Failed to get URL.  HTTP Error {}".format(res[1])
    
        source = title if title else '<' + url + '>'
        msg = 'News source "{}" has been added to subscription list'.format(source)
        return msg


async def remove_feed(db_file, ix):
    # print("remove_feed")
    # print("db_file")
    # print(db_file)
    # time.sleep(1)
    """
    Delete a feed by feed id
    :param conn:
    :param id: id of the feed
    :return: string
    """
    with start_action(action_type="remove_feed()", id=ix):
        with create_connection(db_file) as conn:
            with DBLOCK:
                cur = conn.cursor()
                sql = "SELECT address FROM feeds WHERE id = ?"
                url = cur.execute(sql, (ix,))
                for i in url:
                    url = i[0]
                # NOTE Should we move DBLOCK to this line? 2022-12-23
                sql = "DELETE FROM entries WHERE source = ?"
                cur.execute(sql, (url,))
                sql = "DELETE FROM feeds WHERE id = ?"
                cur.execute(sql, (ix,))
                return """News source <{}> has been removed from subscription list
                       """.format(url)


async def check_feed(db_file, url):
    # print("check_feed")
    # print("db_file")
    # print(db_file)
    # time.sleep(1)
    """
    Check whether a feed exists
    Query for feeds by url
    :param conn:
    :param url:
    :return: row
    """
    with start_action(action_type="check_feed()", url=url):
        cur = get_cursor(db_file)
        sql = "SELECT id FROM feeds WHERE address = ?"
        cur.execute(sql, (url,))
        return cur.fetchone()


async def get_unread(db_file):
    # print("get_unread")
    # print("db_file")
    # print(db_file)
    # time.sleep(1)
    """
    Check read status of entry
    :param conn:
    :param id: id of the entry
    :return: string
    """
    with start_action(action_type="get_unread()", db=db_file):
        with create_connection(db_file) as conn:
            entry = []
            cur = conn.cursor()
            # cur = get_cursor(db_file)
            sql = "SELECT id FROM entries WHERE read = 0"
            ix = cur.execute(sql).fetchone()
            if ix is None:
                return False
            ix = ix[0]
            sql = "SELECT title FROM entries WHERE id = :id"
            cur.execute(sql, (ix,))
            title = cur.fetchone()[0]
            entry.append(title)
            sql = "SELECT summary FROM entries WHERE id = :id"
            cur.execute(sql, (ix,))
            summary = cur.fetchone()[0]
            entry.append(summary)
            sql = "SELECT link FROM entries WHERE id = :id"
            cur.execute(sql, (ix,))
            link = cur.fetchone()[0]
            entry.append(link)
            entry = "{}\n\n{}\n\nLink to article:\n{}".format(entry[0], entry[1], entry[2])
            # print(entry)
            async with DBLOCK:
                await mark_as_read(cur, ix)
            return entry


async def mark_as_read(cur, ix):
    # print("mark_as_read", ix)
    # time.sleep(1)
    """
    Set read status of entry
    :param cur:
    :param ix: index of the entry
    """
    with start_action(action_type="mark_as_read()", id=ix):
        sql = "UPDATE entries SET summary = '', read = 1 WHERE id = ?"
        cur.execute(sql, (ix,))


# TODO mark_all_read for entries of feed
async def toggle_status(db_file, ix):
    # print("toggle_status")
    # print("db_file")
    # print(db_file)
    # time.sleep(1)
    """
    Set status of feed
    :param conn:
    :param id: id of the feed
    :return: string
    """
    with start_action(action_type="toggle_status()", db=db_file):
        async with DBLOCK:
            with create_connection(db_file) as conn:
                cur = conn.cursor()
                #cur = get_cursor(db_file)
                sql = "SELECT name FROM feeds WHERE id = :id"
                cur.execute(sql, (ix,))
                title = cur.fetchone()[0]
                sql = "SELECT enabled FROM feeds WHERE id = ?"
                # NOTE [0][1][2]
                cur.execute(sql, (ix,))
                status = cur.fetchone()[0]
                # FIXME always set to 1
                # NOTE Maybe because is not integer
                # TODO Reset feed table before further testing
                if status == 1:
                    status = 0
                    notice =  "News updates for '{}' are now disabled".format(title)
                else:
                    status = 1
                    notice =  "News updates for '{}' are now enabled".format(title)
                sql = "UPDATE feeds SET enabled = :status WHERE id = :id"
                cur.execute(sql, {"status": status, "id": ix})
        return notice


async def set_date(cur, url):
    # print("set_date")
    # time.sleep(1)
    """
    Set last update date of feed
    :param url: url of the feed
    :return:
    """
    with start_action(action_type="set_date()", url=url):
        today = date.today()
        sql = "UPDATE feeds SET updated = :today WHERE address = :url"
        # cur = conn.cursor()
        cur.execute(sql, {"today": today, "url": url})


async def add_entry_and_set_date(db_file, source, entry):
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            await add_entry(cur, entry)
            await set_date(cur, source)


async def update_source_status(db_file, status, source):
    sql = "UPDATE feeds SET status = :status, scanned = :scanned WHERE address = :url"
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            cur.execute(sql, {"status": status, "scanned": date.today(), "url": source})


async def update_source_validity(db_file, source, valid):
    sql = "UPDATE feeds SET valid = :validity WHERE address = :url"
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            cur.execute(sql, {"validity": valid, "url": source})


async def add_entry(cur, entry):
    # print("add_entry")
    # time.sleep(1)
    """
    Add a new entry into the entries table
    :param conn:
    :param entry:
    :return:
    """
    with start_action(action_type="add_entry()", entry=entry):
        sql = """ INSERT INTO entries(title,summary,link,source,read)
                  VALUES(?,?,?,?,?) """
        # cur = conn.cursor()
        cur.execute(sql, entry)


async def remove_entry(db_file, source, length):
    # print("remove_entry")
    # time.sleep(1)
    """
    Maintain list of entries
    Check the number returned by feed and delete
    existing entries up to the same returned amount
    :param conn:
    :param source:
    :param length:
    :return:
    """
    with start_action(action_type="remove_entry()", source=source):
        # FIXED
        # Dino empty titles are not counted https://dino.im/index.xml
        # SOLVED
        # Add text if is empty
        # title = '*** No title ***' if not entry.title else entry.title
        async with DBLOCK:
            with create_connection(db_file) as conn:
                cur = conn.cursor()
                sql = "SELECT count(id) FROM entries WHERE source = ?"
                count = cur.execute(sql, (source,))
                count = cur.fetchone()[0]
                limit = count - length
                if limit:
                    limit = limit;
                    sql = """DELETE FROM entries WHERE id IN (
                             SELECT id FROM entries
                             WHERE source = :source
                             ORDER BY id
                             ASC LIMIT :limit)"""
                    cur.execute(sql, {"source": source, "limit": limit})


async def get_subscriptions(db_file):
    # print("get_subscriptions")
    # time.sleep(1)
    """
    Query feeds
    :param conn:
    :return: rows (tuple)
    """
    with start_action(action_type="get_subscriptions()"):
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = "SELECT address FROM feeds WHERE enabled = 1"
            cur.execute(sql)
            return cur.fetchall()


async def list_subscriptions(db_file):
    # print("list_subscriptions")
    # print("db_file")
    # print(db_file)
    # time.sleep(1)
    """
    Query feeds
    :param conn:
    :return: rows (string)
    """
    with start_action(action_type="list_subscriptions()", db=db_file):
        with create_connection(db_file) as conn:
            # cur = conn.cursor()
            cur = get_cursor(db_file)
            sql = "SELECT name, address, updated, id, enabled FROM feeds"
            results = cur.execute(sql)
    
        feeds_list = "List of subscriptions: \n"
        counter = 0
        for result in results:
            counter += 1
            feeds_list += """\n{} \n{} \nLast updated: {} \nID: {} [{}]
            """.format(str(result[0]), str(result[1]), str(result[2]),
                       str(result[3]), str(result[4]))
        if counter:
            return feeds_list + "\n Total of {} subscriptions".format(counter)
        else:
            msg = ("List of subscriptions is empty. \n"
                   "To add feed, send a message as follows: \n"
                   "feed add URL \n"
                   "Example: \n"
                   "feed add https://reclaimthenet.org/feed/")
            return msg


async def last_entries(db_file, num):
    # print("last_entries")
    # print("db_file")
    # print(db_file)
    # time.sleep(1)
    """
    Query feeds
    :param conn:
    :param num: integer
    :return: rows (string)
    """
    with start_action(action_type="last_entries()", num=num):
        num = int(num)
        if num > 50:
            num = 50
        elif num < 1:
            num = 1
        with create_connection(db_file) as conn:
            # cur = conn.cursor()
            cur = get_cursor(db_file)
            sql = "SELECT title, link FROM entries ORDER BY ROWID DESC LIMIT :num"
            results = cur.execute(sql, (num,))
    
    
        titles_list = "Recent {} titles: \n".format(num)
        for result in results:
            titles_list += "\n{} \n{}".format(str(result[0]), str(result[1]))
        return titles_list


async def search_entries(db_file, query):
    # print("search_entries")
    # print("db_file")
    # print(db_file)
    # time.sleep(1)
    """
    Query feeds
    :param conn:
    :param query: string
    :return: rows (string)
    """
    with start_action(action_type="search_entries()", query=query):
        if len(query) < 2:
            return "Please enter at least 2 characters to search"

        with create_connection(db_file) as conn:
            # cur = conn.cursor()
            cur = get_cursor(db_file)
            sql = "SELECT title, link FROM entries WHERE title LIKE ? LIMIT 50"
            results = cur.execute(sql, [f'%{query}%'])
    
        results_list = "Search results for '{}': \n".format(query)
        counter = 0
        for result in results:
            counter += 1
            results_list += """\n{} \n{}
            """.format(str(result[0]), str(result[1]))
        if counter:
            return results_list + "\n Total of {} results".format(counter)
        else:
            return "No results found for: {}".format(query)


async def check_entry(db_file, title, link):
    # print("check_entry")
    # time.sleep(1)
    """
    Check whether an entry exists
    Query entries by title and link
    :param conn:
    :param link:
    :param title:
    :return: row
    """
    with start_action(action_type="check_entry()", link=link):
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = "SELECT id FROM entries WHERE title = :title and link = :link"
            cur.execute(sql, {"title": title, "link": link})
            return cur.fetchone()
