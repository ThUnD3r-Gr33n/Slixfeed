#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Based on http_upload.py example from project slixmpp
https://codeberg.org/poezio/slixmpp/src/branch/master/examples/http_upload.py
"""

import logging
from slixmpp.exceptions import IqTimeout
# import sys


async def start(self, jid, filename, domain=None):
    logging.info('Uploading file %s...', filename)
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
        url = await upload_file(
            filename, domain, timeout=10,
        )
    except IqTimeout:
        raise TimeoutError('Could not send message in time')
    logging.info('Upload success!')
    logging.info('Sending file to %s', jid)
    return url
