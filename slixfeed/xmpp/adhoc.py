#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
from datetime import datetime
import logging
import os
import slixfeed.action as action
import slixfeed.config as config
from slixfeed.config import Config
import slixfeed.crawl as crawl
import slixfeed.dt as dt
import slixfeed.fetch as fetch
import slixfeed.url as uri
import slixfeed.sqlite as sqlite
import slixfeed.task as task
from slixfeed.version import __version__
from slixfeed.xmpp.bookmark import XmppBookmark
from slixfeed.xmpp.message import XmppMessage
from slixfeed.xmpp.presence import XmppPresence
from slixfeed.xmpp.roster import XmppRoster
from slixfeed.xmpp.upload import XmppUpload
from slixfeed.xmpp.utility import get_chat_type, is_moderator

class XmppCommand:

# TODO Move class Command to a separate file
# class Command(Slixfeed):
#     def __init__(self):
#         super().__init__()


    def adhoc_commands(self):
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}'.format(function_name))
        # self["xep_0050"].add_command(
        #     node="updates_enable",
        #     name="Enable/Disable News Updates",
        #     handler=option_enable_updates,
        #     )

        # NOTE https://codeberg.org/poezio/slixmpp/issues/3515
        # if jid == self.settings['xmpp']['operator']:
        self['xep_0050'].add_command(node='recent',
                                     name='📰️ Browse',
                                     handler=self._handle_recent)
        self['xep_0050'].add_command(node='subscription',
                                     name='🪶️ Subscribe',
                                     handler=self._handle_subscription_add)
        self['xep_0050'].add_command(node='subscriptions',
                                     name='🎫️ Subscriptions',
                                     handler=self._handle_subscriptions)
        self['xep_0050'].add_command(node='promoted',
                                     name='🔮️ Featured',
                                     handler=self._handle_promoted)
        self['xep_0050'].add_command(node='discover',
                                     name='🔍️ Discover',
                                     handler=self._handle_discover)
        self['xep_0050'].add_command(node='settings',
                                     name='📮️ Settings',
                                     handler=self._handle_settings)
        self['xep_0050'].add_command(node='filters',
                                     name='🛡️ Filters',
                                     handler=self._handle_filters)
        self['xep_0050'].add_command(node='help',
                                     name='📔️ Manual',
                                     handler=self._handle_help)
        self['xep_0050'].add_command(node='advanced',
                                     name='📓 Advanced',
                                     handler=self._handle_advanced)
        self['xep_0050'].add_command(node='profile',
                                     name='💼️ Profile',
                                     handler=self._handle_profile)
        self['xep_0050'].add_command(node='about',
                                     name='📜️ About',
                                     handler=self._handle_about)
        # self['xep_0050'].add_command(node='search',
        #                              name='Search',
        #                              handler=self._handle_search)

    # Special interface
    # http://jabber.org/protocol/commands#actions

    async def _handle_profile(self, iq, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = session['from'].bare
        jid_file = jid_bare
        db_file = config.get_pathname_to_database(jid_file)
        if jid_bare not in self.settings:
            Config.add_settings_jid(self.settings, jid_bare, db_file)
        form = self['xep_0004'].make_form('form', 'Profile')
        form['instructions'] = ('Displaying information\nJabber ID {}'
                                .format(jid_bare))
        form.add_field(ftype='fixed',
                       value='News')
        feeds_all = str(sqlite.get_number_of_items(db_file, 'feeds'))
        form.add_field(label='Subscriptions',
                       ftype='text-single',
                       value=feeds_all)
        feeds_act = str(sqlite.get_number_of_feeds_active(db_file))
        form.add_field(label='Active',
                       ftype='text-single',
                       value=feeds_act)
        entries = sqlite.get_number_of_items(db_file, 'entries')
        archive = sqlite.get_number_of_items(db_file, 'archive')
        entries_all = str(entries + archive)
        form.add_field(label='Items',
                       ftype='text-single',
                       value=entries_all)
        unread = str(sqlite.get_number_of_entries_unread(db_file))
        form.add_field(label='Unread',
                       ftype='text-single',
                       value=unread)
        form.add_field(ftype='fixed',
                       value='Options')
        key_archive = self.settings[jid_bare]['archive'] or self.settings['default']['archive']
        key_archive = str(key_archive)
        form.add_field(label='Archive',
                       ftype='text-single',
                       value=key_archive)
        key_enabled = self.settings[jid_bare]['enabled'] or self.settings['default']['enabled']
        key_enabled = str(key_enabled)
        form.add_field(label='Enabled',
                       ftype='text-single',
                       value=key_enabled)
        key_interval = self.settings[jid_bare]['interval'] or self.settings['default']['interval']
        key_interval = str(key_interval)
        form.add_field(label='Interval',
                       ftype='text-single',
                       value=key_interval)
        key_length = self.settings[jid_bare]['length'] or self.settings['default']['length']
        key_length = str(key_length)
        form.add_field(label='Length',
                       ftype='text-single',
                       value=key_length)
        key_media = self.settings[jid_bare]['media'] or self.settings['default']['media']
        key_media = str(key_media)
        form.add_field(label='Media',
                       ftype='text-single',
                       value=key_media)
        key_old = self.settings[jid_bare]['old'] or self.settings['default']['old']
        key_old = str(key_old)
        form.add_field(label='Old',
                       ftype='text-single',
                       value=key_old)
        key_quantum = self.settings[jid_bare]['quantum'] or self.settings['default']['quantum']
        key_quantum = str(key_quantum)
        form.add_field(label='Quantum',
                       ftype='text-single',
                       value=key_quantum)
        update_interval = self.settings[jid_bare]['interval'] or self.settings['default']['interval']
        update_interval = str(update_interval)
        update_interval = 60 * int(update_interval)
        last_update_time = sqlite.get_last_update_time(db_file)
        if last_update_time:
            last_update_time = float(last_update_time)
            dt_object = datetime.fromtimestamp(last_update_time)
            last_update = dt_object.strftime('%H:%M:%S')
            if int(key_enabled):
                next_update_time = last_update_time + update_interval
                dt_object = datetime.fromtimestamp(next_update_time)
                next_update = dt_object.strftime('%H:%M:%S')
            else:
                next_update = 'n/a'
        else:
            last_update_time = 'n/a'
            next_update = 'n/a'
        form.add_field(ftype='fixed',
                       value='Schedule')
        form.add_field(label='Last update',
                       ftype='text-single',
                       value=last_update)
        form.add_field(label='Next update',
                       ftype='text-single',
                       value=next_update)
        session['payload'] = form
        # text_note = ('Jabber ID: {}'
        #              '\n'
        #              'Last update: {}'
        #              '\n'
        #              'Next update: {}'
        #              ''.format(jid, last_update, next_update))
        # session['notes'] = [['info', text_note]]
        return session

    async def _handle_filters(self, iq, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = session['from'].bare
        chat_type = await get_chat_type(self, jid_bare)
        if chat_type == 'groupchat':
            moderator = is_moderator(self, jid_bare, jid_full)
        if chat_type == 'chat' or moderator:
            jid = session['from'].bare
            jid_file = jid
            db_file = config.get_pathname_to_database(jid_file)
            form = self['xep_0004'].make_form('form', 'Filters')
            form['instructions'] = 'Editing filters' # 🪄️ 🛡️
            value = sqlite.get_filter_value(db_file, 'allow')
            if value: value = str(value[0])
            form.add_field(var='allow',
                           ftype='text-single',
                           label='Allow list',
                           value=value,
                           desc='Keywords to allow (comma-separated keywords).')
            value = sqlite.get_filter_value(db_file, 'deny')
            if value: value = str(value[0])
            form.add_field(var='deny',
                           ftype='text-single',
                           label='Deny list',
                           value=value,
                           desc='Keywords to deny (comma-separated keywords).')
            session['allow_complete'] = True
            session['has_next'] = False
            session['next'] = self._handle_filters_complete
            session['payload'] = form
        else:
            text_warn = ('This resource is restricted to moderators of {}.'
                         .format(jid))
            session['notes'] = [['warn', text_warn]]
        return session


    async def _handle_filters_complete(self, payload, session):
        """
        Process a command result from the user.

        Arguments:
            payload -- Either a single item, such as a form, or a list
                       of items or forms if more than one form was
                       provided to the user. The payload may be any
                       stanza, such as jabber:x:oob for out of band
                       data, or jabber:x:data for typical data forms.
            session -- A dictionary of data relevant to the command
                       session. Additional, custom data may be saved
                       here to persist across handler callbacks.
        """
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        # Text is not displayed; only labels
        form = payload

        jid_bare = session['from'].bare
        # form = self['xep_0004'].make_form('result', 'Done')
        # form['instructions'] = ('✅️ Filters have been updated')
        jid_file = jid_bare
        db_file = config.get_pathname_to_database(jid_file)
        # In this case (as is typical), the payload is a form
        values = payload['values']
        for value in values:
            key = value
            val = values[value]
            # NOTE We might want to add new keywords from
            #      an empty form instead of editing a form.
            # keywords = sqlite.get_filter_value(db_file, key)
            keywords = ''
            val = await config.add_to_list(val, keywords) if val else ''
            if sqlite.is_filter_key(db_file, key):
                await sqlite.update_filter_value(db_file, [key, val])
            elif val:
                await sqlite.set_filter_value(db_file, [key, val])
            # form.add_field(var=key.capitalize() + ' list',
            #                ftype='text-single',
            #                value=val)
        form['title'] = 'Done'
        form['instructions'] = 'has been completed!'
        # session["has_next"] = False
        session['next'] = None
        session['payload'] = form
        return session


    async def _handle_subscription_add(self, iq, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = session['from'].bare
        chat_type = await get_chat_type(self, jid_bare)
        if chat_type == 'groupchat':
            moderator = is_moderator(self, jid_bare, jid_full)
        if chat_type == 'chat' or moderator:
            form = self['xep_0004'].make_form('form', 'Subscription')
            form['instructions'] = 'Adding subscription'
            form.add_field(var='subscription',
                           # TODO Make it possible to add several subscriptions at once;
                           #      Similarly to BitTorrent trackers list
                           # ftype='text-multi',
                           # label='Subscription URLs',
                           # desc=('Add subscriptions one time per '
                           #       'subscription.'),
                           ftype='text-single',
                           label='URL',
                           desc='Enter subscription URL.',
                           value='http://',
                           required=True)
            # form.add_field(var='scan',
            #                ftype='boolean',
            #                label='Scan',
            #                desc='Scan URL for validity (recommended).',
            #                value=True)
            session['allow_prev'] = False
            session['has_next'] = True
            session['next'] = self._handle_subscription_new
            session['prev'] = None
            session['payload'] = form
        else:
            text_warn = ('This resource is restricted to moderators of {}.'
                         .format(jid_bare))
            session['notes'] = [['warn', text_warn]]
        return session


    async def _handle_recent(self, iq, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        form = self['xep_0004'].make_form('form', 'Updates')
        form['instructions'] = 'Browse and read news'
        options = form.add_field(var='action',
                                 ftype='list-single',
                                 label='Read',
                                 desc=('What would you want to read?'),
                                 required=True)
        options.addOption('All news', 'all')
        # options.addOption('News by subscription', 'feed')
        # options.addOption('News by tag', 'tag')
        options.addOption('Rejected news', 'reject')
        options.addOption('Unread news', 'unread')
        session['allow_prev'] = False # Cheogram changes style if that button - which should not be on this form - is present
        session['has_next'] = True
        session['next'] = self._handle_recent_result
        session['payload'] = form
        session['prev'] = None # Cheogram works as expected with 'allow_prev' set to False Just in case
        return session


    async def _handle_recent_result(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = session['from'].bare
        jid_file = jid_bare
        db_file = config.get_pathname_to_database(jid_file)
        num = 100
        match payload['values']['action']:
            case 'all':
                results = sqlite.get_entries(db_file, num)
                subtitle = 'Recent {} updates'.format(num)
                message = 'There are no news'
            case 'reject':
                results = sqlite.get_entries_rejected(db_file, num)
                subtitle = 'Recent {} updates (rejected)'.format(num)
                message = 'There are no rejected news'
            case 'unread':
                results = sqlite.get_unread_entries(db_file, num)
                subtitle = 'Recent {} updates (unread)'.format(num)
                message = 'There are no unread news.'
        if results:
            form = self['xep_0004'].make_form('form', 'Updates')
            form['instructions'] = subtitle
            options = form.add_field(var='update',
                                     ftype='list-single',
                                     label='News',
                                     desc=('Select a news item to read.'),
                                     required=True)
            for result in results:
                title = result[1]
                ix = str(result[0])
                options.addOption(title, ix)
            session['allow_prev'] = False # Cheogram changes style if that button - which should not be on this form - is present
            session['has_next'] = True
            session['next'] = self._handle_recent_select
            session['payload'] = form
            session['prev'] = None # Cheogram works as expected with 'allow_prev' set to False Just in case
        else:
            text_info = message
            session['allow_prev'] = True
            session['has_next'] = False
            session['next'] = None
            session['notes'] = [['info', text_info]]
            session['payload'] = None
            session['prev'] = self._handle_recent
        return session


    async def _handle_recent_select(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        values = payload['values']
        ix = values['update']
        jid_bare = session['from'].bare
        jid_file = jid_bare
        db_file = config.get_pathname_to_database(jid_file)
        title = sqlite.get_entry_title(db_file, ix)
        title = title[0] if title else 'Untitled'
        form = self['xep_0004'].make_form('form', 'Article')
        url = sqlite.get_entry_url(db_file, ix)
        url = url[0]
        logger.debug('Original URL: {}'.format(url))
        url = uri.remove_tracking_parameters(url)
        logger.debug('Processed URL (tracker removal): {}'.format(url))
        url = (uri.replace_hostname(url, 'link')) or url
        logger.debug('Processed URL (replace hostname): {}'.format(url))
        result = await fetch.http(url)
        if 'content' in result:
            data = result['content']
            summary = action.get_document_content_as_text(data)
        else:
            summary = 'No content to show.'
        form.add_field(ftype="text-multi",
                       label=title,
                       value=summary)
        field_url = form.add_field(var='url',
                                   ftype='hidden',
                                   value=url)
        field_url = form.add_field(var='url_link',
                                   label='Link',
                                   ftype='text-single',
                                   value=url)
        field_url['validate']['datatype'] = 'xs:anyURI'
        feed_id = sqlite.get_feed_id_by_entry_index(db_file, ix)
        feed_id = feed_id[0]
        feed_url = sqlite.get_feed_url(db_file, feed_id)
        feed_url = feed_url[0]
        field_feed = form.add_field(var='url_feed',
                                    label='Source',
                                    ftype='text-single',
                                    value=feed_url)
        field_feed['validate']['datatype'] = 'xs:anyURI'
        options = form.add_field(var='filetype',
                                 ftype='list-single',
                                 label='Save as',
                                 desc=('Select file type.'),
                                 value='pdf',
                                 required=True)
        options.addOption('ePUB', 'epub')
        options.addOption('HTML', 'html')
        options.addOption('Markdown', 'md')
        options.addOption('PDF', 'pdf')
        options.addOption('Plain Text', 'txt')
        form['instructions'] = 'Proceed to download article.'
        session['allow_complete'] = False
        session['allow_prev'] = True
        session['has_next'] = True
        session['next'] = self._handle_recent_action
        session['payload'] = form
        session['prev'] = self._handle_recent
        return session


    async def _handle_recent_action(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        ext = payload['values']['filetype']
        url = payload['values']['url'][0]
        jid_bare = session['from'].bare
        jid_file = jid_bare
        db_file = config.get_pathname_to_database(jid_file)
        cache_dir = config.get_default_cache_directory()
        if not os.path.isdir(cache_dir):
            os.mkdir(cache_dir)
        if not os.path.isdir(cache_dir + '/readability'):
            os.mkdir(cache_dir + '/readability')
        url = uri.remove_tracking_parameters(url)
        url = (uri.replace_hostname(url, 'link')) or url
        result = await fetch.http(url)
        if not result['error']:
            data = result['content']
            code = result['status_code']
            title = action.get_document_title(data)
            title = title.strip().lower()
            for i in (' ', '-'):
                title = title.replace(i, '_')
            for i in ('?', '"', '\'', '!'):
                title = title.replace(i, '')
            filename = os.path.join(
                cache_dir, 'readability',
                title + '_' + dt.timestamp() + '.' + ext)
            error = action.generate_document(data, url, ext, filename,
                                             readability=True)
            if error:
                text_error = ('Failed to export {} fot {}'
                              '\n\n'
                              'Reason: {}'.format(ext.upper(), url, error))
                session['notes'] = [['error', text_error]]
            else:
                url = await XmppUpload.start(self, jid_bare, filename)
                form = self['xep_0004'].make_form('result', 'Download')
                form['instructions'] = ('Download {} document.'
                                        .format(ext.upper()))
                field_url = form.add_field(var='url',
                                           label='Link',
                                           ftype='text-single',
                                           value=url)
                field_url['validate']['datatype'] = 'xs:anyURI'
                session['payload'] = form
        session['allow_complete'] = True
        session['next'] = None
        session['prev'] = None
        return session


    async def _handle_subscription_new(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = session['from'].bare
        jid_file = jid_bare
        db_file = config.get_pathname_to_database(jid_file)
        # scan = payload['values']['scan']
        url = payload['values']['subscription']
        if isinstance(url, list) and len(url) > 1:
            url_count = len(url)
            urls = url
            agree_count = 0
            error_count = 0
            exist_count = 0
            for url in urls:
                result = await action.add_feed(self, jid_bare, db_file, url)
                if result['error']:
                    error_count += 1
                elif result['exist']:
                    exist_count += 1
                else:
                    agree_count += 1
            form = self['xep_0004'].make_form('form', 'Subscription')
            if agree_count:
                response = ('Added {} new subscription(s) out of {}'
                            .format(agree_count, url_count))
                session['notes'] = [['info', response]]
            else:
                response = ('No new subscription was added. '
                            'Exist: {} Error: {}.'
                            .format(exist_count, error_count))
                session['notes'] = [['error', response]]
            session['allow_prev'] = True
            session['next'] = None
            session['payload'] = None
            session['prev'] = self._handle_subscription_add
        else:
            if isinstance(url, list):
                url = url[0]
            result = await action.add_feed(self, jid_bare, db_file, url)
            if isinstance(result, list):
                results = result
                form = self['xep_0004'].make_form('form', 'Subscriptions')
                form['instructions'] = ('Discovered {} subscriptions for {}'
                                        .format(len(results), url))
                options = form.add_field(var='subscription',
                                         ftype='list-multi',
                                         label='Subscribe',
                                         desc=('Select subscriptions to add.'),
                                         required=True)
                for result in results:
                    options.addOption(result['name'], result['link'])
                # NOTE Disabling "allow_prev" until Cheogram would allow to display
                # items of list-single as buttons when button "back" is enabled.
                # session['allow_prev'] = True
                session['has_next'] = True
                session['next'] = self._handle_subscription_new
                session['payload'] = form
                # session['prev'] = self._handle_subscription_add
            elif result['error']:
                response = ('Failed to load URL <{}>  Reason: {}'
                            .format(url, result['code']))
                session['allow_prev'] = True
                session['next'] = None
                session['notes'] = [['error', response]]
                session['payload'] = None
                session['prev'] = self._handle_subscription_add
            elif result['exist']:
                # response = ('News source "{}" is already listed '
                #             'in the subscription list at index '
                #             '{}.\n{}'.format(result['name'], result['index'],
                #                              result['link']))
                # session['notes'] = [['warn', response]] # Not supported by Gajim
                # session['notes'] = [['info', response]]
                form = self['xep_0004'].make_form('form', 'Subscription')
                form['instructions'] = ('Subscription is already assigned at index {}.'
                                        '\n'
                                        '{}'
                                        .format(result['index'], result['name']))
                form.add_field(ftype='boolean',
                               var='edit',
                               label='Would you want to edit this subscription?')
                form.add_field(var='subscription',
                               ftype='hidden',
                               value=result['link'])
                # NOTE Should we allow "Complete"?
                # Do all clients provide button "Cancel".
                session['allow_complete'] = False
                session['has_next'] = True
                session['next'] = self._handle_subscription_editor
                session['payload'] = form
                # session['has_next'] = False
            else:
                # response = ('News source "{}" has been '
                #             'added to subscription list.\n{}'
                #             .format(result['name'], result['link']))
                # session['notes'] = [['info', response]]
                form = self['xep_0004'].make_form('form', 'Subscription')
                # form['instructions'] = ('✅️ News source "{}" has been added to '
                #                         'subscription list as index {}'
                #                         '\n\n'
                #                         'Choose next to continue to subscription '
                #                         'editor.'
                #                         .format(result['name'], result['index']))
                form['instructions'] = ('New subscription'
                                        '\n'
                                        '"{}"'
                                        .format(result['name']))
                form.add_field(ftype='boolean',
                               var='edit',
                               label='Continue to edit subscription?')
                form.add_field(var='subscription',
                               ftype='hidden',
                               value=result['link'])
                session['allow_complete'] = False
                session['has_next'] = True
                # session['allow_prev'] = False
                # Gajim: Will offer next dialog but as a result, not as form.
                # session['has_next'] = False
                session['next'] = self._handle_subscription_editor
                session['payload'] = form
                # session['prev'] = None
        return session


    async def _handle_subscription_enable(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        form = payload
        jid_bare = session['from'].bare
        jid_file = jid_bare
        db_file = config.get_pathname_to_database(jid_file)
        ixs = payload['values']['subscriptions']
        form.add_field(ftype='fixed',
                       value='Modified subscriptions')
        for ix in ixs:
            name = sqlite.get_feed_title(db_file, ix)
            url = sqlite.get_feed_url(db_file, ix)
            await sqlite.set_enabled_status(db_file, ix, 1)
            # text = (ix,) + name + url
            # text = ' - '.join(text)
            name = name[0] if name else 'Subscription #{}'.format(ix)
            url = url[0]
            text = '{} <{}>'.format(name, url)
            form.add_field(var=ix,
                           ftype='text-single',
                           label=url,
                           value=text)
        form['type'] = 'result'
        form['title'] = 'Done'
        form['instructions'] = ('Completed successfully!')
        session["has_next"] = False
        session['next'] = None
        session['payload'] = form
        return session


    async def _handle_subscription_disable(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        form = payload
        jid_bare = session['from'].bare
        jid_file = jid_bare
        db_file = config.get_pathname_to_database(jid_file)
        ixs = payload['values']['subscriptions']
        form.add_field(ftype='fixed',
                       value='Modified subscriptions')
        for ix in ixs:
            name = sqlite.get_feed_title(db_file, ix)
            url = sqlite.get_feed_url(db_file, ix)
            await sqlite.set_enabled_status(db_file, ix, 0)
            # text = (ix,) + name + url
            # text = ' - '.join(text)
            name = name[0] if name else 'Subscription #{}'.format(ix)
            url = url[0]
            text = '{} <{}>'.format(name, url)
            form.add_field(var=ix,
                           ftype='text-single',
                           label=url,
                           value=text)
        form['type'] = 'result'
        form['title'] = 'Done'
        form['instructions'] = ('Completed successfully!')
        session["has_next"] = False
        session['next'] = None
        session['payload'] = form
        return session


    async def _handle_subscription_del_complete(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        form = payload
        jid_bare = session['from'].bare
        jid_file = jid_bare
        db_file = config.get_pathname_to_database(jid_file)
        ixs = payload['values']['subscriptions']
        form.add_field(ftype='fixed',
                       value='Deleted subscriptions')
        for ix in ixs:
            name = sqlite.get_feed_title(db_file, ix)
            url = sqlite.get_feed_url(db_file, ix)
            await sqlite.remove_feed_by_index(db_file, ix)
            # text = (ix,) + name + url
            # text = ' - '.join(text)
            name = name[0] if name else 'Subscription #{}'.format(ix)
            url = url[0]
            text = '{} <{}>'.format(name, url)
            form.add_field(var=ix,
                           ftype='text-single',
                           label=url,
                           value=text)
        form['type'] = 'result'
        form['title'] = 'Done'
        form['instructions'] = ('Completed successfully!')
        session["has_next"] = False
        session['next'] = None
        session['payload'] = form
        return session


    def _handle_cancel(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        text_note = ('Operation has been cancelled.'
                     '\n'
                     '\n'
                     'No action was taken.')
        session['notes'] = [['info', text_note]]
        return session


    async def _handle_discover(self, iq, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = session['from'].bare
        chat_type = await get_chat_type(self, jid_bare)
        if chat_type == 'groupchat':
            moderator = is_moderator(self, jid_bare, jid_full)
        if chat_type == 'chat' or moderator:
            form = self['xep_0004'].make_form('form', 'Discover & Search')
            form['instructions'] = 'Discover news subscriptions of all kinds'
            options = form.add_field(var='search_type',
                                     ftype='list-single',
                                     label='Browse',
                                     desc=('Select type of search.'),
                                     required=True)
            options.addOption('All', 'all')
            options.addOption('Categories', 'cat') # Should we write this in a singular form
            # options.addOption('Tags', 'tag')
            session['allow_prev'] = False
            session['has_next'] = True
            session['next'] = self._handle_discover_type
            session['payload'] = form
            session['prev'] = None
        else:
            text_warn = ('This resource is restricted to moderators of {}.'
                         .format(jid_bare))
            session['notes'] = [['warn', text_warn]]
        return session


    def _handle_discover_type(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        values = payload['values']
        search_type = values['search_type']
        config_dir = config.get_default_config_directory()
        db_file = config_dir + '/feeds.sqlite'
        if os.path.isfile(db_file):
            form = self['xep_0004'].make_form('form', 'Discover & Search')
            match search_type:
                case 'all':
                    form['instructions'] = 'Browsing subscriptions'
                    options = form.add_field(var='subscription',
                                             # ftype='list-multi', # TODO To be added soon
                                             ftype='list-single',
                                             label='Subscription',
                                             desc=('Select a subscription to add.'),
                                             required=True)
                    results = sqlite.get_titles_tags_urls(db_file)
                    for result in results:
                        title = result[0]
                        tag = result[1]
                        url = result[2]
                        text = '{} ({})'.format(title, tag)
                        options.addOption(text, url)
                    # session['allow_complete'] = True
                    session['next'] = self._handle_subscription_new
                case 'cat':
                    form['instructions'] = 'Browsing categories'
                    session['next'] = self._handle_discover_category
                    options = form.add_field(var='category',
                                             ftype='list-single',
                                             label='Categories',
                                             desc=('Select a category to browse.'),
                                             required=True) # NOTE Uncategories or no option for entries without category
                    categories = sqlite.get_categories(db_file)
                    for category in categories:
                        category = category[0]
                        options.addOption(category, category)
                # case 'tag':
            session['allow_prev'] = True
            session['has_next'] = True
            session['payload'] = form
            session['prev'] = self._handle_discover
        else:
            text_note = ('Database is missing.'
                         '\n'
                         'Contact operator.')
            session['next'] = None
            session['notes'] = [['info', text_note]]
            session['payload'] = None
        return session


    async def _handle_discover_category(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        values = payload['values']
        category = values['category']
        config_dir = config.get_default_config_directory()
        db_file = config_dir + '/feeds.sqlite'
        form = self['xep_0004'].make_form('form', 'Discover & Search')
        form['instructions'] = 'Browsing category "{}"'.format(category)
        options = form.add_field(var='subscription',
                                 # ftype='list-multi', # TODO To be added soon
                                 ftype='list-single',
                                 label='Subscription',
                                 desc=('Select a subscription to add.'),
                                 required=True)
        results = sqlite.get_titles_tags_urls_by_category(db_file, category)
        for result in results:
            title = result[0]
            tag = result[1]
            url = result[2]
            text = '{} ({})'.format(title, tag)
            options.addOption(text, url)
        # session['allow_complete'] = True
        session['next'] = self._handle_subscription_new
        session['payload'] = form
        return session


    async def _handle_subscriptions(self, iq, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = session['from'].bare
        chat_type = await get_chat_type(self, jid_bare)
        if chat_type == 'groupchat':
            moderator = is_moderator(self, jid_bare, jid_full)
        if chat_type == 'chat' or moderator:
            form = self['xep_0004'].make_form('form', 'Subscriptions')
            form['instructions'] = 'Managing subscriptions'
            options = form.add_field(var='action',
                                     ftype='list-single',
                                     label='Action',
                                     desc='Select action type.',
                                     required=True,
                                     value='browse')
            options.addOption('Browse subscriptions', 'browse')
            options.addOption('Browse subscriptions by tag', 'tag')
            options.addOption('Enable subscriptions', 'enable')
            options.addOption('Disable subscriptions', 'disable')
            options.addOption('Remove subscriptions', 'delete')
            session['payload'] = form
            session['next'] = self._handle_subscriptions_result
            session['has_next'] = True
        else:
            text_warn = ('This resource is restricted to moderators of {}.'
                         .format(jid_bare))
            session['notes'] = [['warn', text_warn]]
        return session


    async def _handle_subscriptions_result(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = session['from'].bare
        jid_file = jid_bare
        db_file = config.get_pathname_to_database(jid_file)
        form = self['xep_0004'].make_form('form', 'Subscriptions')
        match payload['values']['action']:
            case 'browse':
                form['instructions'] = 'Editing subscriptions'
                options = form.add_field(var='subscriptions',
                                         # ftype='list-multi', # TODO To be added soon
                                         ftype='list-single',
                                         label='Subscription',
                                         desc=('Select a subscription to edit.'),
                                         required=True)
                subscriptions = sqlite.get_feeds(db_file)
                subscriptions = sorted(subscriptions, key=lambda x: x[0])
                for subscription in subscriptions:
                    title = subscription[0]
                    url = subscription[1]
                    options.addOption(title, url)
                session['has_next'] = True
                session['next'] = self._handle_subscription_editor
                session['allow_complete'] = False
            case 'delete':
                form['instructions'] = 'Removing subscriptions'
                # form.addField(var='interval',
                #               ftype='text-single',
                #               label='Interval period')
                options = form.add_field(var='subscriptions',
                                         ftype='list-multi',
                                         label='Subscriptions',
                                         desc=('Select subscriptions to remove.'),
                                         required=True)
                subscriptions = sqlite.get_feeds(db_file)
                subscriptions = sorted(subscriptions, key=lambda x: x[0])
                for subscription in subscriptions:
                    title = subscription[0]
                    ix = str(subscription[2])
                    options.addOption(title, ix)
                session['cancel'] = self._handle_cancel
                session['has_next'] = False
                # TODO Refer to confirmation dialog which would display feeds selected
                session['next'] = self._handle_subscription_del_complete
                session['allow_complete'] = True
            case 'disable':
                form['instructions'] = 'Disabling subscriptions'
                options = form.add_field(var='subscriptions',
                                         ftype='list-multi',
                                         label='Subscriptions',
                                         desc=('Select subscriptions to disable.'),
                                         required=True)
                subscriptions = sqlite.get_feeds_by_enabled_state(db_file, True)
                subscriptions = sorted(subscriptions, key=lambda x: x[1])
                for subscription in subscriptions:
                    title = subscription[1]
                    ix = str(subscription[0])
                    options.addOption(title, ix)
                session['cancel'] = self._handle_cancel
                session['has_next'] = False
                session['next'] = self._handle_subscription_disable
                session['allow_complete'] = True
            case 'enable':
                form['instructions'] = 'Enabling subscriptions'
                options = form.add_field(var='subscriptions',
                                         ftype='list-multi',
                                         label='Subscriptions',
                                         desc=('Select subscriptions to enable.'),
                                         required=True)
                subscriptions = sqlite.get_feeds_by_enabled_state(db_file, False)
                subscriptions = sorted(subscriptions, key=lambda x: x[1])
                for subscription in subscriptions:
                    title = subscription[1]
                    ix = str(subscription[0])
                    options.addOption(title, ix)
                session['cancel'] = self._handle_cancel
                session['has_next'] = False
                session['next'] = self._handle_subscription_enable
                session['allow_complete'] = True
            case 'tag':
                form['instructions'] = 'Browsing tags'
                options = form.add_field(var='tag',
                                         ftype='list-single',
                                         label='Tag',
                                         desc=('Select a tag to browse.'),
                                         required=True)
                tags = sqlite.get_tags(db_file)
                tags = sorted(tags, key=lambda x: x[0])
                for tag in tags:
                    name = tag[0]
                    ix = str(tag[1])
                    options.addOption(name, ix)
                session['allow_complete'] = False
                session['next'] = self._handle_subscription_tag
                session['has_next'] = True
        session['allow_prev'] = True
        session['payload'] = form
        session['prev'] = self._handle_subscriptions
        return session


    async def _handle_subscription_tag(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = session['from'].bare
        jid_file = jid_bare
        db_file = config.get_pathname_to_database(jid_file)
        tag_id = payload['values']['tag']
        tag_name = sqlite.get_tag_name(db_file, tag_id)[0]
        form = self['xep_0004'].make_form('form', 'Subscriptions')
        form['instructions'] = 'Subscriptions tagged with "{}"'.format(tag_name)
        options = form.add_field(var='subscriptions',
                                 # ftype='list-multi', # TODO To be added soon
                                 ftype='list-single',
                                 label='Subscription',
                                 desc=('Select a subscription to edit.'),
                                 required=True)
        subscriptions = sqlite.get_feeds_by_tag_id(db_file, tag_id)
        subscriptions = sorted(subscriptions, key=lambda x: x[1])
        for subscription in subscriptions:
            title = subscription[1]
            url = subscription[2]
            options.addOption(title, url)
        session['allow_complete'] = False
        session['allow_prev'] = True
        session['has_next'] = True
        session['next'] = self._handle_subscription_editor
        session['payload'] = form
        session['prev'] = self._handle_subscriptions
        return session


    # FIXME There are feeds that are missing (possibly because of sortings)
    async def _handle_subscription(self, iq, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = session['from'].bare
        form = self['xep_0004'].make_form('form', 'Subscription editor')
        form['instructions'] = '📰️ Edit subscription preferences and properties'
        # form.addField(var='interval',
        #               ftype='text-single',
        #               label='Interval period')
        jid_file = jid_bare
        db_file = config.get_pathname_to_database(jid_file)
        subscriptions = sqlite.get_feeds(db_file)
        # subscriptions = set(subscriptions)
        categorized_subscriptions = {}
        for subscription in subscriptions:
            title = subscription[0]
            url = subscription[1]
            try:
                letter = title[0].capitalize()
                if letter not in categorized_subscriptions:
                    categorized_subscriptions[letter] = [subscription]
                        # title[0].capitalize()] = [subscription]
                else:
                    categorized_subscriptions[letter].append(subscription)
                        # title[0].capitalize()].append(subscription)
            except Exception as e:
                logger.warning('Title might be empty:', str(e))
        for category in sorted(categorized_subscriptions):
            options = form.add_field(var=category,
                                     ftype='list-single',
                                     label=category.capitalize(),
                                     desc='Select a subscription to view.')
            subscriptions_ = categorized_subscriptions[category]
            subscriptions_ = sorted(subscriptions_, key=lambda x: x[0])
            for subscription_ in subscriptions_:
            # for subscription in categorized_subscriptions[category]:
                title = subscription_[0]
                url = subscription_[1]
                options.addOption(title, url)
        session['payload'] = form
        session['next'] = self._handle_subscription_editor
        session['has_next'] = True
        return session


    async def _handle_subscription_editor(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = session['from'].bare
        jid_file = jid_bare
        db_file = config.get_pathname_to_database(jid_file)
        if 'edit' in payload['values'] and not payload['values']['edit']:
            session['payload'] = None
            session['next'] = None
            return session
        if 'subscription' in payload['values']:
            urls = payload['values']['subscription']
        elif 'subscriptions' in payload['values']:
            urls = payload['values']['subscriptions']
        url_count = len(urls)
        form = self['xep_0004'].make_form('form', 'Subscription')
        if isinstance(urls, list) and url_count > 1:
            form['instructions'] = 'Editing {} subscriptions'.format(url_count)
        else:
            if isinstance(urls, list):
                url = urls[0]
            # elif isinstance(urls, str):
            else:
                url = urls
            feed_id = sqlite.get_feed_id(db_file, url)
            if feed_id:
                feed_id = feed_id[0]
                title = sqlite.get_feed_title(db_file, feed_id)
                title = title[0]
                tags_result = sqlite.get_tags_by_feed_id(db_file, feed_id)
                tags_sorted = sorted(x[0] for x in tags_result)
                tags = ', '.join(tags_sorted)
                form['instructions'] = 'Editing subscription #{}'.format(feed_id)
            else:
                form['instructions'] = 'Adding subscription'
                title = ''
                tags = '' # TODO Suggest tags by element "categories"
            form.add_field(ftype='fixed',
                           value='Properties')
            form.add_field(var='name',
                           ftype='text-single',
                           label='Name',
                           value=title,
                           required=True)
            # NOTE This does not look good in Gajim
            # url = form.add_field(ftype='fixed',
            #                      value=url)
            #url['validate']['datatype'] = 'xs:anyURI'
            options = form.add_field(var='url',
                                     ftype='list-single',
                                     label='URL',
                                     value=url)
            options.addOption(url, url)
            feed_id_str = str(feed_id)
            options = form.add_field(var='id',
                                     ftype='list-single',
                                     label='ID #',
                                     value=feed_id_str)
            options.addOption(feed_id_str, feed_id_str)
            form.add_field(var='tags_new',
                           ftype='text-single',
                           label='Tags',
                           desc='Comma-separated tags.',
                           value=tags)
            form.add_field(var='tags_old',
                           ftype='hidden',
                           value=tags)
        form.add_field(ftype='fixed',
                       value='Options')
        options = form.add_field(var='priority',
                                 ftype='list-single',
                                 label='Priority',
                                 value='0')
        options['validate']['datatype'] = 'xs:integer'
        options['validate']['range'] = { 'minimum': 1, 'maximum': 5 }
        i = 0
        while i <= 5:
            num = str(i)
            options.addOption(num, num)
            i += 1
        form.add_field(var='enabled',
                       ftype='boolean',
                       label='Enabled',
                       value=True)
        session['allow_complete'] = True
        # session['allow_prev'] = True
        session['cancel'] = self._handle_cancel
        session['has_next'] = False
        session['next'] = self._handle_subscription_complete
        session['payload'] = form
        return session


    # TODO Create a new form. Do not "recycle" the last form.
    async def _handle_subscription_complete(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = session['from'].bare
        values = payload['values']
        jid_file = jid_bare
        db_file = config.get_pathname_to_database(jid_file)
        # url = values['url']
        # feed_id = sqlite.get_feed_id(db_file, url)
        # feed_id = feed_id[0]
        # if feed_id: feed_id = feed_id[0]
        feed_id = values['id']
        enabled = values['enabled']
        # if enabled:
        #     enabled_status = 1
        # else:
        #     enabled_status = 0
        #     await sqlite.mark_feed_as_read(db_file, feed_id)
        enabled_status = 1 if enabled else 0
        if not enabled_status: await sqlite.mark_feed_as_read(db_file, feed_id)
        await sqlite.set_enabled_status(db_file, feed_id, enabled_status)
        name = values['name']
        await sqlite.set_feed_title(db_file, feed_id, name)
        priority = values['priority']
        tags_new = values['tags_new']
        tags_old = values['tags_old']
        # Add new tags
        for tag in tags_new.split(','):
            tag = tag.strip()
            if not tag:
                continue
            tag = tag.lower()
            tag_id = sqlite.get_tag_id(db_file, tag)
            if not tag_id:
                await sqlite.set_new_tag(db_file, tag)
                tag_id = sqlite.get_tag_id(db_file, tag)
            tag_id = tag_id[0]
            if not sqlite.is_tag_id_of_feed_id(db_file, tag_id, feed_id):
                await sqlite.set_feed_id_and_tag_id(db_file, feed_id, tag_id)
        # Remove tags that were not submitted
        for tag in tags_old[0].split(','):
            tag = tag.strip()
            if not tag:
                continue
            if tag not in tags_new:
                tag_id = sqlite.get_tag_id(db_file, tag)
                tag_id = tag_id[0]
                await sqlite.delete_feed_id_tag_id(db_file, feed_id, tag_id)
                sqlite.is_tag_id_associated(db_file, tag_id)
                await sqlite.delete_tag_by_index(db_file, tag_id)
        # form = self['xep_0004'].make_form('form', 'Subscription')
        # form['instructions'] = ('📁️ Subscription #{} has been {}'
        #                         .format(feed_id, action))
        form = payload
        form['title'] = 'Done'
        form['instructions'] = ('has been completed!')
        # session["has_next"] = False
        session['next'] = None
        session['payload'] = form
        # session['type'] = 'submit'
        return session


    async def _handle_subscription_selector(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = session['from'].bare
        form = self['xep_0004'].make_form('form', 'Add Subscription')
        form['instructions'] = ('📰️ Select a subscription to add\n'
                                'Subsciptions discovered for {}'
                                .format(url))
        # form.addField(var='interval',
        #               ftype='text-single',
        #               label='Interval period')
        options = form.add_field(var='subscriptions',
                                 ftype='list-multi',
                                 label='Subscriptions',
                                 desc=('Select subscriptions to perform '
                                       'actions upon.'),
                                 required=True)
        jid_file = jid_bare
        db_file = config.get_pathname_to_database(jid_file)
        subscriptions = sqlite.get_feeds(db_file)
        subscriptions = sorted(subscriptions, key=lambda x: x[0])
        for subscription in subscriptions:
            title = subscription[0]
            url = subscription[1]
            options.addOption(title, url)
        # options = form.add_field(var='action',
        #                          ftype='list-single',
        #                          label='Action',
        #                          value='none')
        # options.addOption('None', 'none')
        # options.addOption('Reset', 'reset')
        # options.addOption('Enable', 'enable')
        # options.addOption('Disable', 'disable')
        # options.addOption('Delete', 'delete')
        session['payload'] = form
        session['next'] = self._handle_subscription_editor
        session['has_next'] = True
        return session


    async def _handle_advanced(self, iq, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = session['from'].bare
        chat_type = await get_chat_type(self, jid_bare)
        if chat_type == 'groupchat':
            moderator = is_moderator(self, jid_bare, jid_full)
        if chat_type == 'chat' or moderator:
            form = self['xep_0004'].make_form('form', 'Advanced')
            form['instructions'] = 'Extended options'
            options = form.add_field(var='option',
                                     ftype='list-single',
                                     label='Choose',
                                     required=True)
            # options.addOption('Activity', 'activity')
            # options.addOption('Filters', 'filter')
            # options.addOption('Statistics', 'statistics')
            # options.addOption('Scheduler', 'scheduler')
            options.addOption('Import', 'import')
            options.addOption('Export', 'export')
            jid = session['from'].bare
            if jid == self.settings['xmpp']['operator']:
                options.addOption('Administration', 'admin')
            session['payload'] = form
            session['next'] = self._handle_advanced_result
            session['has_next'] = True
        else:
            text_warn = ('This resource is restricted to moderators of {}.'
                         .format(jid))
            session['notes'] = [['warn', text_warn]]
        return session


    async def _handle_advanced_result(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        match payload['values']['option']:
            case 'activity':
                # TODO dialog for JID and special dialog for operator
                # Here you can monitor activity
                text_note = 'This feature is not yet available.'
                session['notes'] = [['info', text_note]]
            case 'admin':
                # NOTE Even though this check is already conducted on previous
                # form, this check is being done just in case.
                jid_bare = session['from'].bare
                if jid_bare == self.settings['xmpp']['operator']:
                    if self.is_component:
                        # NOTE This will be changed with XEP-0222 XEP-0223
                        text_info = ('Subscriber management options are '
                                     'currently not available for Slixfeed '
                                     'running as component. Once support for '
                                     'XEP-0222 and XEP-0223 be added, this '
                                     'panel will be usable for components as '
                                     'well.')
                        session['has_next'] = False
                        session['next'] = None
                        session['notes'] = [['info', text_info]]
                    else:
                        form = self['xep_0004'].make_form('form', 'Admin Panel')
                        form['instructions'] = 'Administration actions'
                        options = form.add_field(var='action',
                                                 ftype='list-single',
                                                 label='Manage',
                                                 desc='Select action type.',
                                                 value='subscribers',
                                                 required=True)
                        options.addOption('Bookmarks', 'bookmarks')
                        options.addOption('Contacts', 'roster')
                        options.addOption('Subscribers', 'subscribers')
                        session['payload'] = form
                        session['next'] = self._handle_admin_action
                        session['has_next'] = True
                else:
                    logger.warning('An unauthorized attempt to access '
                                   'bookmarks has been detected for JID {} at '
                                   '{}'.format(jid_bare, dt.timestamp()))
                    text_warn = 'This resource is restricted.'
                    session['notes'] = [['warn', text_warn]]
                    session['has_next'] = False
                    session['next'] = None
            # case 'filters':
                # TODO Ability to edit lists.toml or filters.toml
            case 'scheduler':
                # TODO Set days and hours to receive news
                text_note = 'This feature is not yet available.'
                session['notes'] = [['info', text_note]]
                session['has_next'] = False
                session['next'] = None
            case 'statistics':
                # TODO Here you can monitor statistics
                text_note = 'This feature is not yet available.'
                session['notes'] = [['info', text_note]]
                session['has_next'] = False
                session['next'] = None
            case 'import':
                form = self['xep_0004'].make_form('form', 'Import')
                form['instructions'] = 'Importing feeds'
                url = form.add_field(var='url',
                                     ftype='text-single',
                                     label='URL',
                                     desc='Enter URL to an OPML file.',
                                     required=True)
                url['validate']['datatype'] = 'xs:anyURI'
                session['allow_complete'] = True
                session['has_next'] = False
                session['next'] = self._handle_import_complete
                session['payload'] = form
            case 'export':
                form = self['xep_0004'].make_form('form', 'Export')
                form['instructions'] = ('To easily import subscriptions from '
                                        'one News Reader to another, then it '
                                        'is always recommended to export '
                                        'subscriptions into OPML file. See '
                                        'About -> Software for a list of '
                                        'News Readers offered for desktop and '
                                        'mobile devices.')
                options = form.add_field(var='filetype',
                                         ftype='list-multi',
                                         label='Format',
                                         desc='Choose export format.',
                                         value='opml',
                                         required=True)
                options.addOption('Markdown', 'md')
                options.addOption('OPML', 'opml')
                # options.addOption('HTML', 'html')
                # options.addOption('XBEL', 'xbel')
                session['allow_complete'] = True
                session['has_next'] = False
                session['next'] = self._handle_export_complete
                session['payload'] = form
        session['allow_prev'] = True
        session['prev'] = self._handle_advanced
        return session


    async def _handle_about(self, iq, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        form = self['xep_0004'].make_form('form', 'About')
        form['instructions'] = 'Information about Slixfeed and related projects'
        options = form.add_field(var='option',
                                 ftype='list-single',
                                 label='About',
                                 required=True)
        config_dir = config.get_default_config_directory()
        with open(config_dir + '/' + 'information.toml', mode="rb") as information:
            entries = tomllib.load(information)
        for entry in entries:
            label = entries[entry][0]['title']
            options.addOption(label, entry)
            # options.addOption('Tips', 'tips')
        session['payload'] = form
        session['next'] = self._handle_about_result
        session['has_next'] = True
        return session


    async def _handle_about_result(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        config_dir = config.get_default_config_directory()
        with open(config_dir + '/' + 'information.toml', mode="rb") as information:
            entries = tomllib.load(information)
        entry_key = payload['values']['option']
            # case 'terms':
            #     title = 'Policies'
            #     subtitle = 'Terms and Conditions'
            #     content = action.manual('information.toml', 'terms')
            # case 'tips':
            #     # Tips and tricks you might have not known about Slixfeed and XMPP!
            #     title = 'Help'
            #     subtitle = 'Tips & Tricks'
            #     content = 'This page is not yet available.'
            # case 'translators':
            #     title = 'Translators'
            #     subtitle = 'From all across the world'
            #     content = action.manual('information.toml', 'translators')
        # title = entry_key.capitalize()
        # form = self['xep_0004'].make_form('result', title)
        for entry in entries[entry_key]:
            if 'title' in entry:
                title = entry['title']
                form = self['xep_0004'].make_form('result', title)
                subtitle = entry['subtitle']
                form['instructions'] = subtitle
                continue
            for e_key in entry:
                e_val = entry[e_key]
                e_key = e_key.capitalize()
                # form.add_field(ftype='fixed',
                #                value=e_val)
                print(type(e_val))
                if e_key == 'Name':
                    form.add_field(ftype='fixed',
                                    value=e_val)
                    continue
                if isinstance(e_val, list):
                    form_type = 'text-multi'
                else:
                    form_type = 'text-single'
                form.add_field(label=e_key,
                               ftype=form_type,
                               value=e_val)
        # Gajim displays all form['instructions'] on top
        # Psi ignore the latter form['instructions']
        # form['instructions'] = 'YOU!\n🫵️\n- Join us -'
        session['payload'] = form
        session['allow_complete'] = True
        session['allow_prev'] = True
        session["has_next"] = False
        session['next'] = None
        # session['payload'] = None # Crash Cheogram
        session['prev'] = self._handle_about
        return session


    async def _handle_motd(self, iq, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        # TODO add functionality to attach image.
        # Here you can add groupchat rules,post schedule, tasks or
        # anything elaborated you might deem fit. Good luck!
        text_note = 'This feature is not yet available.'
        session['notes'] = [['info', text_note]]
        return session


    async def _handle_help(self, iq, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))

        config_dir = config.get_default_config_directory()
        with open(config_dir + '/' + 'commands.toml', mode="rb") as commands:
            cmds = tomllib.load(commands)

        form = self['xep_0004'].make_form('result', 'Manual')
        form['instructions'] = '🛟️ Help manual for interactive chat'

        # text = '🛟️ Help and Information about Slixfeed\n\n'
        # for cmd in cmds:
        #     name = cmd.capitalize()
        #     elements = cmds[cmd]
        #     text += name + '\n'
        #     for key, value in elements.items():
        #         text += " " + key.capitalize() + '\n'
        #         for line in value.split("\n"):
        #             text += "  " + line + '\n'
        # form['instructions'] = text

        for cmd in cmds:
            name = cmd.capitalize()
            form.add_field(var='title',
                           ftype='fixed',
                           value=name)
            elements = cmds[cmd]
            for key, value in elements.items():
                key = key.replace('_', ' ')
                key = key.capitalize()
                form.add_field(var='title',
                               ftype='text-multi',
                               label=key,
                               value=value)
        session['payload'] = form
        return session


    async def _handle_import_complete(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        form = payload
        url = payload['values']['url']
        if url.startswith('http') and url.endswith('.opml'):
            jid_bare = session['from'].bare
            jid_file = jid_bare.replace('/', '_')
            db_file = config.get_pathname_to_database(jid_file)
            count = await action.import_opml(db_file, url)
            try:
                int(count)
                # form = self['xep_0004'].make_form('result', 'Done')
                # form['instructions'] = ('✅️ Feeds have been imported')
                form['title'] = 'Done'
                form['instructions'] = ('has been completed!')
                message = '{} feeds have been imported.'.format(count)
                form.add_field(var='Message',
                               ftype='text-single',
                               value=message)
                session['payload'] = form
            except:
                session['payload'] = None
                text_error = ('Import failed. Filetype does not appear to be '
                              'an OPML file.')
                session['notes'] = [['error', text_error]]
        else:
            session['payload'] = None
            text_error = 'Import aborted. Send URL of OPML file.'
            session['notes'] = [['error', text_error]]
        session["has_next"] = False
        session['next'] = None
        return session


    async def _handle_export_complete(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        form = payload
        jid_bare = session['from'].bare
        jid_file = jid_bare.replace('/', '_')
        # form = self['xep_0004'].make_form('result', 'Done')
        # form['instructions'] = ('✅️ Feeds have been exported')
        exts = payload['values']['filetype']
        for ext in exts:
            filename = await action.export_feeds(self, jid_bare, jid_file, ext)
            url = await XmppUpload.start(self, jid_bare, filename)
            url_field = form.add_field(var=ext.upper(),
                                       ftype='text-single',
                                       label=ext,
                                       value=url)
            url_field['validate']['datatype'] = 'xs:anyURI'
            chat_type = await get_chat_type(self, jid_bare)
            XmppMessage.send_oob(self, jid_bare, url, chat_type)
        form['type'] = 'result'
        form['title'] = 'Done'
        form['instructions'] = ('Completed successfully!')
        session["has_next"] = False
        session['next'] = None
        session['payload'] = form
        return session


    # TODO Exclude feeds that are already in database or requester.
    # TODO Attempt to look up for feeds of hostname of JID (i.e. scan
    # jabber.de for feeds for juliet@jabber.de)
    async def _handle_promoted(self, iq, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = session['from'].bare
        jid_full = str(session['from'])
        chat_type = await get_chat_type(self, jid_bare)
        if chat_type == 'groupchat':
            moderator = is_moderator(self, jid_bare, jid_full)
        if chat_type == 'chat' or moderator:
            form = self['xep_0004'].make_form('form', 'Subscribe')
            # NOTE Refresh button would be of use
            form['instructions'] = 'Featured subscriptions'
            url = action.pick_a_feed()
            # options = form.add_field(var='choice',
            #                          ftype="boolean",
            #                          label='Subscribe to {}?'.format(url['name']),
            #                          desc='Click to subscribe.')
            # form.add_field(var='subscription',
            #                 ftype='hidden',
            #                 value=url['link'])
            options = form.add_field(var='subscription',
                                      ftype="list-single",
                                      label='Subscribe',
                                      desc='Click to subscribe.')
            for i in range(10):
                url = action.pick_a_feed()
                options.addOption(url['name'], url['link'])
            jid = session['from'].bare
            if '@' in jid:
                hostname = jid.split('@')[1]
                url = 'http://' + hostname
            result = await crawl.probe_page(url)
            if not result:
                url = {'url' : url,
                        'index' : None,
                        'name' : None,
                        'code' : None,
                        'error' : True,
                        'exist' : False}
            elif isinstance(result, list):
                for url in result:
                    if url['link']: options.addOption('{}\n{}'.format(url['name'], url['link']), url['link'])
            else:
                url = result
                # Automatically set priority to 5 (highest)
                if url['link']: options.addOption(url['name'], url['link'])
            session['allow_complete'] = False
            session['allow_prev'] = True
            # singpolyma: Don't use complete action if there may be more steps
            # https://gitgud.io/sjehuda/slixfeed/-/merge_requests/13
            # Gajim: On next form Gajim offers no button other than "Commands".
            # Psi: Psi closes the dialog.
            # Conclusion, change session['has_next'] from False to True
            # session['has_next'] = False
            session['has_next'] = True
            session['next'] = self._handle_subscription_new
            session['payload'] = form
            session['prev'] = self._handle_promoted
        else:
            text_warn = ('This resource is restricted to moderators of {}.'
                         .format(jid))
            session['notes'] = [['warn', text_warn]]
        return session


    async def _handle_admin_action(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = session['from'].bare
        jid_file = jid_bare
        db_file = config.get_pathname_to_database(jid_file)
        subscriptions = sqlite.get_feeds(db_file)
        subscriptions = sorted(subscriptions, key=lambda x: x[0])
        form = self['xep_0004'].make_form('form', 'Subscriptions')
        match payload['values']['action']:
            case 'bookmarks':
                form = self['xep_0004'].make_form('form', 'Bookmarks')
                form['instructions'] = 'Bookmarks'
                options = form.add_field(var='jid',
                                         ftype='list-single',
                                         label='Jabber ID',
                                         desc='Select a bookmark to edit.',
                                         required=True)
                conferences = await XmppBookmark.get(self)
                for conference in conferences:
                    options.addOption(conference['name'], conference['jid'])
                session['has_next'] = True
                session['next'] = self._handle_bookmarks_editor
            case 'roster':
                form = self['xep_0004'].make_form('form', 'Contacts')
                form['instructions'] = 'Organize contacts'
                options = form.add_field(var='jid',
                                         ftype='list-single',
                                         label='Contact',
                                         desc='Select a contact.',
                                         required=True)
                contacts = await XmppRoster.get_contacts(self)
                for contact in contacts:
                    contact_name = contacts[contact]['name']
                    contact_name = contact_name if contact_name else contact
                    options.addOption(contact_name, contact)
                options = form.add_field(var='action',
                                         ftype='list-single',
                                         label='Action',
                                         required=True)
                options.addOption('Display', 'view')
                options.addOption('Edit', 'edit')
                session['has_next'] = True
                session['next'] = self._handle_contact_action
            case 'subscribers':
                form = self['xep_0004'].make_form('form', 'Subscribers')
                form['instructions'] = 'Committing subscriber action'
                options = form.add_field(var='action',
                                         ftype='list-single',
                                         label='Action',
                                         value='message',
                                         required=True)
                options.addOption('Request authorization From', 'from')
                options.addOption('Resend authorization To', 'to')
                options.addOption('Send message', 'message')
                options.addOption('Remove', 'remove')
                options = form.add_field(var='jid',
                                         ftype='list-single',
                                         label='Jabber ID',
                                         desc='Select a contact.',
                                         required=True)
                contacts = await XmppRoster.get_contacts(self)
                for contact in contacts:
                    contact_name = contacts[contact]['name']
                    contact_name = contact_name if contact_name else contact
                    options.addOption(contact_name, contact)
                form.add_field(var='subject',
                               ftype='text-single',
                               label='Subject')
                form.add_field(var='message',
                               ftype='text-multi',
                               label='Message',
                               desc='Add a descriptive message.')
                session['allow_complete'] = True
                session['has_next'] = False
                session['next'] = self._handle_subscribers_complete
        session['allow_prev'] = True
        session['payload'] = form
        session['prev'] = self._handle_advanced
        return session


    async def _handle_subscribers_complete(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        values = payload['values']
        jid_bare = values['jid']
        value_subject = values['subject']
        message_subject = value_subject if value_subject else None
        value_message = values['message']
        message_body = value_message if value_message else None
        match values['action']:
            case 'from':
                XmppPresence.subscription(self, jid_bare, 'subscribe')
                if not message_subject:
                    message_subject = 'System Message'
                if not message_body:
                    message_body = ('This user wants to subscribe to your '
                                    'presence. Click the button labelled '
                                    '"Add/Auth" toauthorize the subscription. '
                                    'This will also add the person to your '
                                    'contact list if it is not already there.')
            case 'remove':
                XmppRoster.remove(self, jid_bare)
                if not message_subject:
                    message_subject = 'System Message'
                if not message_body:
                    message_body = 'Your authorization has been removed!'
            case 'to':
                XmppPresence.subscription(self, jid_bare, 'subscribed')
                if not message_subject:
                    message_subject = 'System Message'
                if not message_body:
                    message_body = 'Your authorization has been approved!'
        if message_subject:
            XmppMessage.send_headline(self, jid_bare, message_subject,
                                      message_body, 'chat')
        elif message_body:
            XmppMessage.send(self, jid_bare, message_body, 'chat')
        form = payload
        form['title'] = 'Done'
        form['instructions'] = ('has been completed!')
        # session["has_next"] = False
        session['next'] = None
        session['payload'] = form
        return session


    async def _handle_contact_action(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = payload['values']['jid']
        form = self['xep_0004'].make_form('form', 'Contacts')
        session['allow_complete'] = True
        roster = await XmppRoster.get_contacts(self)
        properties = roster[jid_bare]
        match payload['values']['action']:
            case 'edit':
                form['instructions'] = 'Editing contact'
                options = form.add_field(var='jid',
                                         ftype='list-single',
                                         label='Jabber ID',
                                         value=jid_bare)
                options.addOption(jid_bare, jid_bare)
                form.add_field(var='name',
                               ftype='text-single',
                               label='Name',
                               value=properties['name'])
                session['allow_complete'] = True
                session['next'] = self._handle_contacts_complete
            case 'view':
                form['instructions'] = 'Viewing contact'
                contact_name = properties['name']
                contact_name = contact_name if contact_name else jid_bare
                form.add_field(var='name',
                               ftype='text-single',
                               label='Name',
                               value=properties['name'])
                form.add_field(var='from',
                               ftype='boolean',
                               label='From',
                               value=properties['from'])
                form.add_field(var='to',
                               ftype='boolean',
                               label='To',
                               value=properties['to'])
                form.add_field(var='pending_in',
                               ftype='boolean',
                               label='Pending in',
                               value=properties['pending_in'])
                form.add_field(var='pending_out',
                               ftype='boolean',
                               label='Pending out',
                               value=properties['pending_out'])
                form.add_field(var='whitelisted',
                               ftype='boolean',
                               label='Whitelisted',
                               value=properties['whitelisted'])
                form.add_field(var='subscription',
                               ftype='fixed',
                               label='Subscription',
                               value=properties['subscription'])
                session['allow_complete'] = None
                session['next'] = None
        # session['allow_complete'] = True
        session['allow_prev'] = True
        session['has_next'] = False
        # session['next'] = None
        session['payload'] = form
        session['prev'] = self._handle_contacts_complete
        return session


    def _handle_contacts_complete(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        values = payload['values']
        jid_bare = values['jid']
        name = values['name']
        name_old = XmppRoster.get_contact_name(self, jid_bare)
        if name == name_old:
            message = ('No action has been taken.  Reason: New '
                       'name is identical to the current one.')
            session['payload'] = None
            session['notes'] = [['info', message]]
        else:
            XmppRoster.set_contact_name(self, jid_bare, name)
            form = payload
            form['title'] = 'Done'
            form['instructions'] = ('has been completed!')
            session['payload'] = form
        session['next'] = None
        return session


    async def _handle_bookmarks_editor(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = payload['values']['jid']
        properties = await XmppBookmark.properties(self, jid_bare)
        form = self['xep_0004'].make_form('form', 'Bookmarks')
        form['instructions'] = 'Editing bookmark'
        jid_split = properties['jid'].split('@')
        room = jid_split[0]
        host = jid_split[1]
        options = form.addField(var='jid',
                                ftype='list-single',
                                label='Jabber ID',
                                value=jid_bare)
        options.addOption(jid_bare, jid_bare)
        form.addField(var='name',
                      ftype='text-single',
                      label='Name',
                      value=properties['name'],
                      required=True)
        form.addField(var='room',
                      ftype='text-single',
                      label='Room',
                      value=room,
                      required=True)
        form.addField(var='host',
                      ftype='text-single',
                      label='Host',
                      value=host,
                      required=True)
        form.addField(var='alias',
                      ftype='text-single',
                      label='Alias',
                      value=properties['nick'],
                      required=True)
        form.addField(var='password',
                      ftype='text-private',
                      label='Password',
                      value=properties['password'])
        form.addField(var='language',
                      ftype='text-single',
                      label='Language',
                      value=properties['lang'])
        form.add_field(var='autojoin',
                       ftype='boolean',
                       label='Auto-join',
                       value=properties['autojoin'])
        # options = form.add_field(var='action',
        #                ftype='list-single',
        #                label='Action',
        #                value='join')
        # options.addOption('Add', 'add')
        # options.addOption('Join', 'join')
        # options.addOption('Remove', 'remove')
        session['allow_complete'] = True
        session['allow_prev'] = True
        session['has_next'] = False
        session['next'] = self._handle_bookmarks_complete
        session['payload'] = form
        session['prev'] = self._handle_admin_action
        return session


    async def _handle_bookmarks_complete(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        # form = self['xep_0004'].make_form('result', 'Done')
        # form['instructions'] = ('✅️ Bookmark has been saved')
        # # In this case (as is typical), the payload is a form
        values = payload['values']
        await XmppBookmark.add(self, properties=values)
        # for value in values:
        #     key = str(value)
        #     val = str(values[value])
        #     if not val: val = 'None' # '(empty)'
        #     form.add_field(var=key,
        #                     ftype='text-single',
        #                     label=key.capitalize(),
        #                     value=val)
        form = payload
        form['title'] = 'Done'
        form['instructions'] = 'has been completed!'
        session['next'] = None
        session['payload'] = form
        return session


    async def _handle_settings(self, iq, session):
        """
        Respond to the initial request for a command.
    
        Arguments:
            iq      -- The iq stanza containing the command request.
            session -- A dictionary of data relevant to the command
                       session. Additional, custom data may be saved
                       here to persist across handler callbacks.
        """
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                    .format(function_name, jid_full))
        jid_bare = session['from'].bare
        chat_type = await get_chat_type(self, jid_bare)
        if chat_type == 'groupchat':
            moderator = is_moderator(self, jid_bare, jid_full)
        if chat_type == 'chat' or moderator:
            jid_file = jid_bare
            db_file = config.get_pathname_to_database(jid_file)
            if jid_bare not in self.settings:
                Config.add_settings_jid(self.settings, jid_bare, db_file)
            form = self['xep_0004'].make_form('form', 'Settings')
            form['instructions'] = 'Editing settings'
            value = self.settings[jid_bare]['enabled'] or self.settings['default']['enabled']
            value = str(value)
            value = int(value)
            if value:
                value = True
            else:
                value = False
            form.add_field(var='enabled',
                           ftype='boolean',
                           label='Enabled',
                           desc='Enable news updates.',
                           value=value)
            value = self.settings[jid_bare]['media'] or self.settings['default']['media']
            value = str(value)
            value = int(value)
            if value:
                value = True
            else:
                value = False
            form.add_field(var='media',
                           ftype='boolean',
                           desc='Send audio, images or videos if found.',
                           label='Display media',
                           value=value)
            value = self.settings[jid_bare]['old'] or self.settings['default']['old']
            value = str(value)
            value = int(value)
            if value:
                value = True
            else:
                value = False
            form.add_field(var='old',
                           ftype='boolean',
                           desc='Treat all items of newly added subscriptions as new.',
                           # label='Send only new items',
                           label='Include old news',
                           value=value)
            value = self.settings[jid_bare]['interval'] or self.settings['default']['interval']
            value = str(value)
            value = int(value)
            value = value/60
            value = int(value)
            value = str(value)
            options = form.add_field(var='interval',
                                     ftype='list-single',
                                     label='Interval',
                                     desc='Interval update (in hours).',
                                     value=value)
            options['validate']['datatype'] = 'xs:integer'
            options['validate']['range'] = { 'minimum': 1, 'maximum': 48 }
            i = 1
            while i <= 48:
                x = str(i)
                options.addOption(x, x)
                if i >= 12:
                    i += 6
                else:
                    i += 1
            value = self.settings[jid_bare]['quantum'] or self.settings['default']['quantum']
            value = str(value)
            options = form.add_field(var='quantum',
                                     ftype='list-single',
                                     label='Amount',
                                     desc='Amount of items per update.',
                                     value=value)
            options['validate']['datatype'] = 'xs:integer'
            options['validate']['range'] = { 'minimum': 1, 'maximum': 5 }
            i = 1
            while i <= 5:
                x = str(i)
                options.addOption(x, x)
                i += 1
            value = self.settings[jid_bare]['archive'] or self.settings['default']['archive']
            value = str(value)
            options = form.add_field(var='archive',
                                     ftype='list-single',
                                     label='Archive',
                                     desc='Number of news items to archive.',
                                     value=value)
            options['validate']['datatype'] = 'xs:integer'
            options['validate']['range'] = { 'minimum': 0, 'maximum': 500 }
            i = 0
            while i <= 500:
                x = str(i)
                options.addOption(x, x)
                i += 50
            session['allow_complete'] = True
            # session['has_next'] = True
            session['next'] = self._handle_settings_complete
            session['payload'] = form
        else:
            text_warn = ('This resource is restricted to moderators of {}.'
                         .format(jid_bare))
            session['notes'] = [['warn', text_warn]]
        return session


    async def _handle_settings_complete(self, payload, session):
        jid_full = str(session['from'])
        function_name = sys._getframe().f_code.co_name
        logger.debug('{}: jid_full: {}'
                     .format(function_name, jid_full))
        jid_bare = session['from'].bare
        form = payload
        jid_file = jid_bare
        db_file = config.get_pathname_to_database(jid_file)
        if jid_bare not in self.settings:
            Config.add_settings_jid(self.settings, jid_bare, db_file)
        # In this case (as is typical), the payload is a form
        values = payload['values']
        for value in values:
            key = value
            val = values[value]

            if key in ('enabled', 'media', 'old'):
                if val == True:
                    val = 1
                elif val == False:
                    val = 0

            if key in ('archive', 'interval', 'quantum'):
                val = int(val)

            if key == 'interval':
                if val < 1: val = 1
                val = val * 60

            is_enabled = self.settings[jid_bare]['enabled'] or self.settings['default']['enabled']

            if (key == 'enabled' and
                val == 1 and
                str(is_enabled) == 0):
                logger.info('Slixfeed has been enabled for {}'.format(jid_bare))
                status_type = 'available'
                status_message = '📫️ Welcome back!'
                XmppPresence.send(self, jid_bare, status_message,
                                  status_type=status_type)
                await asyncio.sleep(5)
                key_list = ['check', 'status', 'interval']
                await task.start_tasks_xmpp_chat(self, jid_bare, key_list)

            if (key == 'enabled' and
                val == 0 and
                str(is_enabled) == 1):
                logger.info('Slixfeed has been disabled for {}'.format(jid_bare))
                key_list = ['interval', 'status']
                task.clean_tasks_xmpp_chat(self, jid_bare, key_list)
                status_type = 'xa'
                status_message = '📪️ Send "Start" to receive updates'
                XmppPresence.send(self, jid_bare, status_message,
                                  status_type=status_type)

            await Config.set_setting_value(self.settings, jid_bare, db_file, key, val)
            val = self.settings[jid_bare][key]

            # if key == 'enabled':
            #     if str(setting.enabled) == 0:
            #         status_type = 'available'
            #         status_message = '📫️ Welcome back!'
            #         XmppPresence.send(self, jid, status_message,
            #                           status_type=status_type)
            #         await asyncio.sleep(5)
            #         await task.start_tasks_xmpp_chat(self, jid, ['check', 'status',
            #                                                 'interval'])
            #     else:
            #         task.clean_tasks_xmpp_chat(self, jid, ['interval', 'status'])
            #         status_type = 'xa'
            #         status_message = '📪️ Send "Start" to receive Jabber updates'
            #         XmppPresence.send(self, jid, status_message,
            #                           status_type=status_type)

            if key in ('enabled', 'media', 'old'):
                if val == '1':
                    val = 'Yes'
                elif val == '0':
                    val = 'No'

            if key == 'interval':
                val = int(val)
                val = val/60
                val = int(val)
                val = str(val)

            # match value:
            #     case 'enabled':
            #         pass
            #     case 'interval':
            #         pass

            # result = '{}: {}'.format(key.capitalize(), val)

            # form.add_field(var=key,
            #                 ftype='fixed',
            #                 value=result)
        form['title'] = 'Done'
        form['instructions'] = 'has been completed!'
        # session['allow_complete'] = True
        # session['has_next'] = False
        # session['next'] = self._handle_profile
        session['payload'] = form
        return session
