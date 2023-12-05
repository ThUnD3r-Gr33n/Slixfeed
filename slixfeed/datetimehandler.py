#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
https://feedparser.readthedocs.io/en/latest/date-parsing.html
"""

from datetime import datetime
from dateutil.parser import parse
from email.utils import parsedate, parsedate_to_datetime

async def now():
    """
    ISO 8601 Timestamp.

    Returns
    -------
    date : ?
        ISO 8601 Timestamp.
    """
    date = datetime.now().isoformat()
    return date


async def current_time():
    """
    Print HH:MM:SS timestamp.

    Returns
    -------
    date : ?
        HH:MM:SS timestamp.
    """
    now = datetime.now()
    time = now.strftime("%H:%M:%S")
    return time


async def validate(date):
    """
    Validate date format.

    Parameters
    ----------
    date : str
        Timestamp.

    Returns
    -------
    date : str
        Timestamp.
    """
    try:
        parse(date)
    except:
        date = now()
    return date


async def rfc2822_to_iso8601(date):
    """
    Convert RFC 2822 into ISO 8601.

    Parameters
    ----------
    date : str
        RFC 2822 Timestamp.

    Returns
    -------
    date : str
        ISO 8601 Timestamp.
    """
    if parsedate(date):
        try:
            date = parsedate_to_datetime(date)
            date = date.isoformat()
        except:
            date = now()
    return date
