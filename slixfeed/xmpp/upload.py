#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Based on http_upload.py example from project slixmpp
https://codeberg.org/poezio/slixmpp/src/branch/master/examples/http_upload.py
"""

from pathlib import Path
from slixfeed.log import Logger
from slixmpp import JID
from slixmpp.exceptions import IqTimeout, IqError
from slixmpp.plugins.xep_0363.http_upload import HTTPError
import sys
from typing import Optional

logger = Logger(__name__)
# import sys

class XmppUpload:

    async def start(self, jid, filename: Path, size: Optional[int] = None,
                    encrypted: bool = False, domain: Optional[JID] = None):
        logger.info(['Uploading file %s...', filename])
        try:
            upload_file = self['xep_0363'].upload_file
            if encrypted and not self['xep_0454']:
                print(
                    'The xep_0454 module isn\'t available. '
                    'Ensure you have \'cryptography\' '
                    'from extras_require installed.',
                    file=sys.stderr,
                )
                url = None
            elif encrypted:
                upload_file = self['xep_0454'].upload_file
            try:
                url = await upload_file(filename, size, domain, timeout=10,)
                logger.info('Upload successful!')
                logger.info(['Sending file to %s', jid])
            except HTTPError:
                url = None
                logger.error('It appears that this server does not support '
                             'HTTP File Upload.')
                # raise HTTPError(
                #     "This server doesn't appear to support HTTP File Upload"
                #     )
        except IqError as e:
            url = None
            logger.error('Could not send message')
            logger.error(e)
        except IqTimeout as e:
            url = None
            # raise TimeoutError('Could not send message in time')
            logger.error('Could not send message in time')
            logger.error(e)
        return url
