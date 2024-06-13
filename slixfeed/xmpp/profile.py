#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

NOTE

The VCard XML fields that can be set are as follows:
    ‘FN’, ‘NICKNAME’, ‘URL’, ‘BDAY’, ‘ROLE’, ‘NOTE’, ‘MAILER’,
    ‘TZ’, ‘REV’, ‘UID’, ‘DESC’, ‘TITLE’, ‘PRODID’, ‘SORT-STRING’,
    ‘N’, ‘ADR’, ‘TEL’, ‘EMAIL’, ‘JABBERID’, ‘ORG’, ‘CATEGORIES’,
    ‘NOTE’, ‘PRODID’, ‘REV’, ‘SORT-STRING’, ‘SOUND’, ‘UID’, ‘URL’,
    ‘CLASS’, ‘KEY’, ‘MAILER’, ‘GEO’, ‘TITLE’, ‘ROLE’,
    ‘LOGO’, ‘AGENT’

TODO

1) Test XEP-0084.

2) Make sure to support all type of servers.
    
3) Catch IqError
    ERROR:slixmpp.basexmpp:internal-server-error: Database failure
    WARNING:slixmpp.basexmpp:You should catch IqError exceptions

"""

import glob
from slixfeed.config import Config
import slixfeed.config as config
from slixfeed.log import Logger
from slixmpp.exceptions import IqTimeout, IqError
import os

logger = Logger(__name__)

# class XmppProfile:

async def update(self):
    """ Update profile """
    try:
        await set_vcard(self)
    except IqTimeout as e:
        logger.error('Profile vCard: Error Timeout')
        logger.error(str(e))
    except IqError as e:
            logger.error('Profile vCard: Error XmppIQ')
            logger.error(str(e))
    try:
        await set_avatar(self)
    except IqTimeout as e:
        logger.error('Profile Photo: Error Timeout')
        logger.error(str(e))
    except IqError as e:
            logger.error('Profile Photo: Error XmppIQ')
            logger.error(str(e))


async def set_avatar(self):
    config_dir = config.get_default_config_directory()
    if not os.path.isdir(config_dir):
        config_dir = '/usr/share/slixfeed/'
    filename = glob.glob(config_dir + '/image.*')
    if not filename and os.path.isdir('/usr/share/slixfeed/'):
        # filename = '/usr/share/slixfeed/image.svg'
        filename = glob.glob('/usr/share/slixfeed/image.*')
    if not filename:
        config_dir = os.path.dirname(__file__)
        config_dir = config_dir.split('/')
        config_dir.pop()
        config_dir = '/'.join(config_dir)
        filename = glob.glob(config_dir + '/assets/image.*')
    if len(filename):
        filename = filename[0]
        image_file = os.path.join(config_dir, filename)
        with open(image_file, 'rb') as avatar_file:
            avatar = avatar_file.read()
            # await self.plugin['xep_0084'].publish_avatar(avatar)
            try:
                await self.plugin['xep_0153'].set_avatar(avatar=avatar)
            except IqTimeout as e:
                logger.error('Profile Photo: Error Timeout 222')
                logger.error(str(e))
            except IqError as e:
                    logger.error('Profile Photo: Error XmppIQ 222')
                    logger.error(str(e))


def set_identity(self, category):
    """
    Identify for Service Descovery.

    Parameters
    ----------
    category : str
        "client" or "service".

    Returns
    -------
    None.

    """
    self['xep_0030'].add_identity(
        category=category,
        itype='news',
        name='slixfeed',
        node=None,
        jid=self.boundjid.full,
    )


async def set_vcard(self):
    vcard = self.plugin['xep_0054'].make_vcard()
    profile = config.get_values('accounts.toml', 'xmpp')['profile']
    for key in profile:
        vcard[key] = profile[key]
    await self.plugin['xep_0054'].publish_vcard(vcard)

