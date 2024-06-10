#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# print("Initiating IPC server...")
# print("Shutting down IPC server...")

"""
TODO Exchange socket fd and send a command to delete
socket (i.e. clients[fd]) from the respective client.
"""

import asyncio
import os
import slixfeed.config as config
from slixfeed.xmpp.commands import XmppCommands
import socket

class XmppIpcServer:

    """
    Inter-Process Communication interface of type Berkeley sockets.
    """

    async def ipc(self):

        ipc_socket_filename = '/tmp/slixfeed_xmpp.socket'

        # Setup socket
        if os.path.exists(ipc_socket_filename):
            os.remove(ipc_socket_filename)

        loop = asyncio.get_running_loop()

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(ipc_socket_filename)
        sock.listen(0)

        # conn = None
        # clients = []
        # clients = {}

        # Start listening loop
        while True:
            # Accept 'request'
            conn, addr = await loop.sock_accept(sock)

            # # Terminate an old connection in favour of a new connection
            # if len(clients):
            #     for c in clients:
            #         print(c)
            #         c.close()
            #         del c
            # else:
            #     conn, addr = await loop.sock_accept(sock)
            #     clients.append(conn)
            #     print(clients)

            # Manage connections inside a dict
            # fd = conn.fileno()
            # clients[fd] = conn

            # datastream = await loop.sock_recv(conn, 1024)
            # if datastream.decode('utf-8') == 'identifier':
            #     await loop.sock_sendall(conn, fd.encode('utf-8'))

            print('A connection from client has been detected. '
                  'Slixfeed is waiting for commands.')
            # print('There are {} clients connected to the IPC '
            #       'interface'.format(len(clients)))
            # Process 'request'
            while True:
                response = None

                # print('Awaiting for a command')
                # print(clients[fd])

                datastream = await loop.sock_recv(conn, 1024)
                if not datastream:
                    break
                data = datastream.decode('utf-8')
                if '~' in data:
                    data_list = data.split('~')
                    jid_bare = data_list[0]
                    db_file = config.get_pathname_to_database(jid_bare)
                    command = data_list[1]
                else:
                    command = data
                match command:
                    case _ if command.startswith('add '):
                        command = command[4:]
                        url = command.split(' ')[0]
                        title = ' '.join(command.split(' ')[1:])
                        response = XmppCommands.feed_add(
                            url, db_file, jid_bare, title)
                    case _ if command.startswith('allow +'):
                            val = command[7:]
                            if val:
                                await XmppCommands.set_filter_allow(
                                    db_file, val, True)
                                response = ('Approved keywords\n'
                                            '```\n{}\n```'
                                            .format(val))
                            else:
                                response = ('No action has been taken.'
                                            '\n'
                                            'Missing keywords.')
                    case _ if command.startswith('allow -'):
                            val = command[7:]
                            if val:
                                await XmppCommands.set_filter_allow(
                                    db_file, val, False)
                                response = ('Approved keywords\n'
                                            '```\n{}\n```'
                                            .format(val))
                            else:
                                response = ('No action has been taken.'
                                            '\n'
                                            'Missing keywords.')
                    case _ if command.startswith('archive'):
                        val = command[8:]
                        response = await XmppCommands.set_archive(
                            self, jid_bare, val)
                    case _ if command.startswith('bookmark +'):
                        muc_jid = command[11:]
                        response = await XmppCommands.bookmark_add(
                            self, muc_jid)
                    case _ if command.startswith('bookmark -'):
                        muc_jid = command[11:]
                        response = await XmppCommands.bookmark_del(
                            self, muc_jid)
                    case 'bookmarks':
                        response = await XmppCommands.print_bookmarks(self)
                    case _ if command.startswith('clear '):
                        key = command[6:]
                        response = await XmppCommands.clear_filter(db_file, key)
                    case _ if command.startswith('default '):
                        key = command[8:]
                        response = await XmppCommands.restore_default(
                            self, jid_bare, key=None)
                    case 'defaults':
                        response = await XmppCommands.restore_default(self, jid_bare)
                    case _ if command.startswith('deny +'):
                            val = command[6:]
                            if val:
                                await XmppCommands.set_filter_allow(
                                    db_file, val, True)
                                response = ('Rejected keywords\n'
                                            '```\n{}\n```'
                                            .format(val))
                            else:
                                response = ('No action has been taken.'
                                            '\n'
                                            'Missing keywords.')
                    case _ if command.startswith('deny -'):
                            val = command[6:]
                            if val:
                                await XmppCommands.set_filter_allow(
                                    db_file, val, False)
                                response = ('Rejected keywords\n'
                                            '```\n{}\n```'
                                            .format(val))
                            else:
                                response = ('No action has been taken.'
                                            '\n'
                                            'Missing keywords.')
                    case _ if command.startswith('disable '):
                        response = await XmppCommands.feed_disable(
                            self, db_file, jid_bare, command)
                    case _ if command.startswith('enable '):
                        response = await XmppCommands.feed_enable(
                            self, db_file, command)
                    case _ if command.startswith('export'):
                        ext = command[7:]
                        if ext in ('md', 'opml'):
                            filename, result = XmppCommands.export_feeds(
                                self, jid_bare, ext)
                            response = result + ' : ' + filename
                        else:
                            response = 'Unsupported filetype.  Try: md or opml'
                    case _ if command.startswith('feeds'):
                        query = command[6:]
                        result, number = XmppCommands.list_feeds(db_file, query)
                        if number:
                            if query:
                                first_line = ('Subscriptions containing "{}":\n'
                                              .format(query))
                            else:
                                first_line = 'Subscriptions:\n'
                            response = (first_line + result +
                                        '\nTotal of {} feeds'.format(number))
                    case _ if (command.startswith('gemini:') or
                               command.startswith('gopher:')):
                        response = XmppCommands.fetch_gemini()
                    case 'help':
                        response = XmppCommands.print_help()
                    case 'help all':
                        response = XmppCommands.print_help_list()
                    case _ if (command.startswith('http') and
                               command.endswith('.opml')):
                        response = await XmppCommands.import_opml(
                            self, db_file, jid_bare, command)
                    case 'info':
                        response = XmppCommands.print_info_list()
                    case _ if command.startswith('info'):
                        entry = command[5:].lower()
                        response = XmppCommands.print_info_specific(entry)
                    case 'pubsub list':
                        response = await XmppCommands.pubsub_list(
                            self, jid_bare)
                    case _ if command.startswith('pubsub list '):
                        jid = command[12:]
                        response = 'List of nodes for {}:\n```\n'.format(jid)
                        response = await XmppCommands.pubsub_list(self, jid)
                        response += '```'
                    case _ if command.startswith('pubsub send '):
                        info = command[12:]
                        info = info.split(' ')
                        jid = info[0]
                        # num = int(info[1])
                        if jid:
                            response = XmppCommands.pubsub_send(self, info, jid)
                    # TODO Handle node error
                    # sqlite3.IntegrityError: UNIQUE constraint failed: feeds_pubsub.node
                    # ERROR:slixmpp.basexmpp:UNIQUE constraint failed: feeds_pubsub.node
                    case _ if (command.startswith('http') or
                               command.startswith('feed:/') or
                               command.startswith('itpc:/') or
                               command.startswith('rss:/')):
                        response = await XmppCommands.fetch_http(
                            self, command, db_file, jid_bare)
                    case _ if command.startswith('interval'):
                        val = command[9:]
                        if val:
                            response = await XmppCommands.set_interval(
                                self, db_file, jid_bare, val)
                        else:
                            response = 'Current value for interval: '
                            response += XmppCommands.get_interval(self, jid_bare)
                    case _ if command.startswith('join'):
                        muc_jid = command[5:]
                        response = await XmppCommands.muc_join(self, muc_jid)
                    case _ if command.startswith('length'):
                            val = command[7:]
                            if val:
                                response = await XmppCommands.set_length(
                                    self, db_file, jid_bare, val)
                            else:
                                response = 'Current value for length: '
                                response += XmppCommands.get_length(self, jid_bare)
                    case 'media off':
                        response = await XmppCommands.set_media_off(
                            self, jid_bare, db_file)
                    case 'media on':
                        response = await XmppCommands.set_media_on(
                            self, jid_bare, db_file)
                    case 'new':
                        response = await XmppCommands.set_old_off(
                            self, jid_bare, db_file)
                    case _ if command.startswith('next'):
                        await XmppCommands.send_next_update(self, jid_bare, command)
                    case _ if command.startswith('node delete '):
                        info = command[12:]
                        info = info.split(' ')
                        response = XmppCommands.node_delete(self, info)
                    case _ if command.startswith('node purge '):
                        info = command[11:]
                        info = info.split(' ')
                        response = XmppCommands.node_purge(self, info)
                    case 'old':
                        response = await XmppCommands.set_old_on(
                            self, jid_bare, db_file)
                    case 'options':
                        response = 'Options:\n```'
                        response += XmppCommands.print_options(self, jid_bare)
                        response += '\n```'
                    case _ if command.startswith('quantum'):
                        val = command[8:]
                        if val:
                            response = await XmppCommands.set_quantum(
                                self, db_file, jid_bare, val)
                        else:
                            response = 'Quantum: '
                            response += XmppCommands.get_quantum(
                                self, jid_bare)
                    case 'random':
                        response = XmppCommands.set_random(self, jid_bare, db_file)
                    case _ if command.startswith('read '):
                        data = command[5:]
                        data = data.split()
                        url = data[0]
                        if url:
                            response = await XmppCommands.feed_read(
                                self, jid_bare, data, url)
                        else:
                            response = ('No action has been taken.'
                                        '\n'
                                        'Missing URL.')
                    case _ if command.startswith('recent'):
                        num = command[7:]
                        if not num: num = 5
                        count, result = XmppCommands.print_recent(
                            self, db_file, num)
                        if count:
                            response = 'Recent {} fetched titles:\n'.format(num)
                            response += result
                        else:
                            response = result
                    case _ if command.startswith('remove '):
                        ix_url = command[7:]
                        ix_url = ix_url.split(' ')
                        response = await XmppCommands.feed_remove(
                            self, jid_bare, db_file, ix_url)
                    case _ if command.startswith('rename '):
                        response = await XmppCommands.feed_rename(
                            self, db_file, jid_bare, command)
                    case _ if command.startswith('reset'):
                        ix_url = command[6:]
                        ix_url = ix_url.split(' ')
                        response = await XmppCommands.mark_as_read(
                            self, jid_bare, db_file, ix_url)
                    case _ if command.startswith('search'):
                        query = command[7:]
                        response = XmppCommands.search_items(
                            self, db_file, query)
                    case 'start':
                        response = await XmppCommands.scheduler_start(
                            self, db_file, jid_bare)
                    case 'stats':
                        response = XmppCommands.print_statistics(db_file)
                    case 'stop':
                        response = await XmppCommands.scheduler_stop(
                            self, db_file, jid_bare)
                    case 'support':
                        response = XmppCommands.print_support_jid()
                    case 'version':
                        response = XmppCommands.print_version(self, jid_bare)
                    case _ if command.startswith('xmpp:'):
                        response = await XmppCommands.muc_join(self, command)
                    case _ if command.startswith('xmpp:'):
                        response = await XmppCommands.muc_join(self, command)
                    case 'exit':
                        conn.close()
                        break
                    case _:
                        response = XmppCommands.print_unknown()
                # Send 'response'
                await loop.sock_sendall(conn, response.encode('utf-8'))
