#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Based on http_upload.py example from project slixmpp
https://codeberg.org/poezio/slixmpp/src/branch/master/examples/http_upload.py
"""

from slixfeed.log import Logger
from slixmpp.exceptions import IqTimeout, IqError
from slixmpp.plugins.xep_0363.http_upload import HTTPError

logger = Logger(__name__)
# import sys

class XmppUpload:

    async def start(self, jid, filename, domain=None):
        logger.info('Uploading file %s...', filename)
        try:
            upload_file = self['xep_0363'].upload_file
            # if self.encrypted and not self['xep_0454']:
            #     print(
            #         'The xep_0454 module isn\'t available. '
            #         'Ensure you have \'cryptography\' '
            #         'from extras_require installed.',
            #         file=sys.stderr,
            #     )
            #     return
            # elif self.encrypted:
            #     upload_file = self['xep_0454'].upload_file
            try:
                url = await upload_file(
                    filename, domain, timeout=10,
                )
                logger.info('Upload successful!')
                logger.info('Sending file to %s', jid)
            except HTTPError:
                url = ('Error: It appears that this server does not support '
                       'HTTP File Upload.')
                logger.error('It appears that this server does not support '
                             'HTTP File Upload.')
                # raise HTTPError(
                #     "This server doesn't appear to support HTTP File Upload"
                #     )
        except IqError as e:
            logger.error('Could not send message')
            logger.error(e)
        except IqTimeout as e:
            # raise TimeoutError('Could not send message in time')
            logger.error('Could not send message in time')
            logger.error(e)
        return url
