#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
https://feedparser.readthedocs.io/en/latest/date-parsing.html
"""

from datetime import datetime
from dateutil.parser import parse
from email.utils import parsedate, parsedate_to_datetime

def now():
    """
    ISO 8601 Timestamp.

    Returns
    -------
    date : ???
        ISO 8601 Timestamp.
    """
    date = datetime.now().isoformat()
    return date


def convert_struct_time_to_iso8601(struct_time):
    date = datetime(*struct_time[:6])
    date = date.isoformat()
    return date


def current_date():
    """
    Print MM DD, YYYY (Weekday Time) timestamp.

    Returns
    -------
    date : str
        MM DD, YYYY (Weekday Time) timestamp.
    """
    now = datetime.now()
    time = now.strftime("%B %d, %Y (%A %T)")
    return time


def current_time():
    """
    Print HH:MM:SS timestamp.

    Returns
    -------
    date : str
        HH:MM:SS timestamp.
    """
    now = datetime.now()
    time = now.strftime("%H:%M:%S")
    return time


def timestamp():
    """
    Print time stamp to be used in filename.

    Returns
    -------
    formatted_time : str
        %Y%m%d-%H%M%S timestamp.
    """
    now = datetime.now()
    formatted_time = now.strftime("%Y%m%d-%H%M%S")
    return formatted_time


def validate(date):
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


def rfc2822_to_iso8601(date):
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
