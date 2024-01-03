#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from slixfeed.datetime import current_date

def markdown(jid, filename, results):
    with open(filename, 'w') as file:
        file.write(
            '# Subscriptions for {}\n'.format(jid))
        file.write(
            '## Set of feeds exported with Slixfeed\n')
        for result in results:
            file.write(
                '- [{}]({})\n'.format(result[0], result[1]))
        file.write(
            '\n\n* * *\n\nThis list was saved on {} from xmpp:{} using '
            '[Slixfeed](https://gitgud.io/sjehuda/slixfeed)\n'.format(
                current_date(), jid))
