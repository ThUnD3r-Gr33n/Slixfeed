#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from sqlite3 import Error

import asyncio

from datetime import date

# from eliot import start_action, to_file
# # with start_action(action_type="list_subscriptions()", db=db_file):
# # with start_action(action_type="last_entries()", num=num):
# # with start_action(action_type="get_subscriptions()"):
# # with start_action(action_type="remove_entry()", source=source):
# # with start_action(action_type="search_entries()", query=query):
# # with start_action(action_type="check_entry()", link=link):

# aiosqlite
DBLOCK = asyncio.Lock()

CURSORS = {}

def create_connection(db_file):
    """
    Create a database connection to the SQLite database
    specified by db_file.
    
    :param db_file: Database filename.
    :return: Connection object or None.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)
    return conn


def create_tables(db_file):
    """
    Create SQLite tables.
    
    :param db_file: Database filename.
    """
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
        # statistics_table_sql = """
        #     CREATE TABLE IF NOT EXISTS statistics (
        #         id integer PRIMARY KEY,
        #         title text NOT NULL,
        #         number integer
        #     ); """
    
        c = conn.cursor()
        # c = get_cursor(db_file)
        c.execute(feeds_table_sql)
        c.execute(entries_table_sql)
        # c.execute(statistics_table_sql)


def get_cursor(db_file):
    """
    Allocate a cursor to connection per database.
    
    :param db_file: Database filename.
    :return: Cursor.
    """
    if db_file in CURSORS:
        return CURSORS[db_file]
    else:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            CURSORS[db_file] = cur
    return CURSORS[db_file]


async def add_feed(db_file, feed, url, res):
    """
    Add a new feed into the feeds table.
    
    :param db_file: Database filename.
    :param feed: Parsed XML document.
    :param url: URL.
    :param res: XML document.
    :return: Message.
    """
    #TODO consider async with DBLOCK
    #conn = create_connection(db_file)

    # with create_connection(db_file) as conn:
    #     #exist = await check_feed_exist(conn, url)
    #     exist = await check_feed_exist(db_file, url)

    # if not exist:
    #     res = await main.download_feed(url)
    # else:
    #     return "News source is already listed in the subscription list"

    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            title = feed["feed"]["title"]
            feed = (title, url, 1, res[1], 1)
            sql = """INSERT INTO feeds(name,address,enabled,status,valid)
                     VALUES(?,?,?,?,?) """
            cur.execute(sql, feed)

    source = title if title else '<' + url + '>'
    msg = 'News source "{}" has been added to subscription list'.format(source)
    return msg


async def remove_feed(db_file, ix):
    """
    Delete a feed by feed id.
    
    :param db_file: Database filename.
    :param ix: Index of feed.
    :return: Message.
    """
    with create_connection(db_file) as conn:
        async with DBLOCK:
            cur = conn.cursor()
            try:
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
            except:
                return """No news source with ID {}""".format(ix)


async def check_feed_exist(db_file, url):
    """
    Check whether a feed exists.
    Query for feeds by given url.
    
    :param db_file: Database filename.
    :param url: URL.
    :return: SQL row or None.
    """
    cur = get_cursor(db_file)
    sql = "SELECT id FROM feeds WHERE address = ?"
    cur.execute(sql, (url,))
    return cur.fetchone()


async def get_number_of_items(db_file, str):
    """
    Return number of entries or feeds.
    
    :param cur: Cursor object.
    :param str: "entries" or "feeds".
    :return: Number of rows.
    """
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = "SELECT count(id) FROM {}".format(str)
        count = cur.execute(sql)
        count = cur.fetchone()[0]
        return count


async def get_number_of_entries_unread(db_file):
    """
    Return number of unread items.
    
    :param db_file: Database filename.
    :param cur: Cursor object.
    :return: Number of rows.
    """
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = "SELECT count(id) FROM entries WHERE read = 0"
        count = cur.execute(sql)
        count = cur.fetchone()[0]
        return count


async def get_entry_unread(db_file):
    """
    Check read status of entry.
    
    :param db_file: Database filename.
    :return: News item as message.
    """
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        entry = []
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
        entry = "{}\n\n{}\n\n{}".format(entry[0], entry[1], entry[2])
        # print(entry)
        async with DBLOCK:
            await mark_as_read(cur, ix)
        # async with DBLOCK:
        #     await update_statistics(db_file)
        return entry


async def mark_as_read(cur, ix):
    """
    Set read status of entry.
    
    :param cur: Cursor object.
    :param ix: Index of entry.
    """
    sql = "UPDATE entries SET summary = '', read = 1 WHERE id = ?"
    cur.execute(sql, (ix,))


async def statistics(db_file):
    """
    Return table statistics.
    
    :param db_file: Database filename.
    :return: News item as message.
    """
    feeds = await get_number_of_items(db_file, 'feeds')
    entries = await get_number_of_items(db_file, 'entries')
    unread_entries = await get_number_of_entries_unread(db_file)
    return "You have {} unread news items out of {} from {} news sources.".format(unread_entries, entries, feeds)


async def update_statistics(cur):
    """
    Update table statistics.
    
    :param cur: Cursor object.
    """
    stat_dict = {}
    stat_dict["feeds"] = await get_number_of_items(cur, 'feeds')
    stat_dict["entries"] = await get_number_of_items(cur, 'entries')
    stat_dict["unread"] = await get_number_of_entries_unread(cur=cur)
    for i in stat_dict:
        sql = "SELECT id FROM statistics WHERE title = ?"
        cur.execute(sql, (i,))
        if cur.fetchone():
            sql = "UPDATE statistics SET number = :num WHERE title = :title"
            cur.execute(sql, {"title": i, "num": stat_dict[i]})
        else:
            sql = "SELECT count(id) FROM statistics"
            count = cur.execute(sql)
            count = cur.fetchone()[0]
            ix = count + 1
            sql = "INSERT INTO statistics VALUES(?,?,?)"
            cur.execute(sql, (ix, i, stat_dict[i]))


# TODO mark_all_read for entries of feed
async def toggle_status(db_file, ix):
    """
    Toggle status of feed.
    
    :param db_file: Database filename.
    :param ix: Index of entry.
    :return: Message
    """
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
                state =  "disabled"
            else:
                status = 1
                state = "enabled"
            sql = "UPDATE feeds SET enabled = :status WHERE id = :id"
            cur.execute(sql, {"status": status, "id": ix})
    return "Updates for '{}' are now {}".format(title, state)


async def set_date(cur, url):
    """
    Set last update date of feed.
    
    :param cur: Cursor object.
    :param url: URL.
    """
    today = date.today()
    sql = "UPDATE feeds SET updated = :today WHERE address = :url"
    # cur = conn.cursor()
    cur.execute(sql, {"today": today, "url": url})


async def add_entry_and_set_date(db_file, source, entry):
    """
    TODO
    """
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            await add_entry(cur, entry)
            await set_date(cur, source)


async def update_source_status(db_file, status, source):
    """
    TODO
    """
    sql = "UPDATE feeds SET status = :status, scanned = :scanned WHERE address = :url"
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            cur.execute(sql, {"status": status, "scanned": date.today(), "url": source})


async def update_source_validity(db_file, source, valid):
    """
    TODO
    """
    sql = "UPDATE feeds SET valid = :validity WHERE address = :url"
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            cur.execute(sql, {"validity": valid, "url": source})


async def add_entry(cur, entry):
    """
    Add a new entry into the entries table.
    
    :param cur: Cursor object.
    :param entry:
    """
    sql = """ INSERT INTO entries(title,summary,link,source,read)
              VALUES(?,?,?,?,?) """
    cur.execute(sql, entry)


# This function doesn't work as expected with bbs and wiki feeds
async def remove_entry(db_file, source, length):
    """
    Maintain list of entries equal to feed.
    Check the number returned by feed and delete
    existing entries up to the same returned amount.
    
    :param db_file: Database filename.
    :param source:
    :param length:
    :return:
    """
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


async def remove_nonexistent_entries(db_file, feed, source):
    """
    Remove entries that don't exist in a given parsed feed.
    Check the entries returned from feed and delete non
    existing entries
    
    :param db_file: Database filename.
    :param feed: URL of parsed feed.
    :param source: URL of associated feed.
    """
    async with DBLOCK:
        with create_connection(db_file) as conn:
            cur = conn.cursor()
            sql = "SELECT id, title, link FROM entries WHERE source = ?"
            cur.execute(sql, (source,))
            entries_db = cur.fetchall()
            # print('entries_db')
            # print(entries_db)
            for entry_db in entries_db:
                # entry_db[1] = id
                # entry_db[2] = title
                # entry_db[3] = link
                exist = False
                # print("check-db")
                for entry_feed in feed.entries:
                    # print("check-feed")
                    # TODO better check and don't repeat code
                    if entry_feed.has_key("title"):
                        title = entry_feed.title
                    else:
                        title = feed["feed"]["title"]
    
                    if entry_feed.has_key("link"):
                        link = entry_feed.link
                    else:
                        link = source
                    # TODO better check and don't repeat code
                    if entry_db[1] == title and entry_db[2] == link:
                        # print('exist')
                        # print(title)
                        exist = True
                        break
                if not exist:
                    # print('>>> not exist')
                    # print(entry_db[1])
                    # TODO Send to table archive
                    # TODO Also make a regular/routine check for sources that have been changed (though that can only happen when manually editing)
                    sql = "DELETE FROM entries WHERE id = ?"
                    cur.execute(sql, (entry_db[0],))
            # breakpoint()


async def get_subscriptions(db_file):
    """
    Query table feeds.
    
    :param db_file: Database filename.
    :return: List of feeds.
    """
    with create_connection(db_file) as conn:
        cur = conn.cursor()
        sql = "SELECT address FROM feeds WHERE enabled = 1"
        cur.execute(sql)
        return cur.fetchall()


async def list_subscriptions(db_file):
    """
    Query table feeds and list items.
    
    :param db_file: Database filename.
    :return: List of feeds.
    """
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
               "add https://reclaimthenet.org/feed/")
        return msg


async def last_entries(db_file, num):
    """
    Query entries
    
    :param db_file: Database filename.
    :param num: Number
    :return: List of recent N entries
    """
    num = int(num)
    if num > 50:
        num = 50
    elif num < 1:
        num = 1
    cur = get_cursor(db_file)
    sql = "SELECT title, link FROM entries ORDER BY ROWID DESC LIMIT :num"
    results = cur.execute(sql, (num,))


    titles_list = "Recent {} titles: \n".format(num)
    for result in results:
        titles_list += "\n{} \n{}".format(str(result[0]), str(result[1]))
    return titles_list


async def search_entries(db_file, query):
    """
    Query entries
    
    :param db_file: Database filename.
    :param query: Search query
    :return: Entries with specified keywords
    """
    if len(query) < 2:
        return "Please enter at least 2 characters to search"

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


async def check_entry_exist(db_file, title, link):
    """
    Check whether an entry exists.
    Query entries by title and link.
    
    :param db_file: Database filename.
    :param link: Entry URL.
    :param title: Entry title.
    :return: SQL row or None.
    """
    cur = get_cursor(db_file)
    sql = "SELECT id FROM entries WHERE title = :title and link = :link"
    cur.execute(sql, {"title": title, "link": link})
    return cur.fetchone()
