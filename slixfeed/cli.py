#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
# from slixfeed.log import Logger
import socket
import sys

# logger = Logger(__name__)

# IPC parameters
ipc_socket_filename = '/tmp/slixfeed_xmpp.socket'

# Init socket object
if not os.path.exists(ipc_socket_filename):
    print(f"File {ipc_socket_filename} doesn't exists")
    sys.exit(-1)
 
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.connect(ipc_socket_filename)

# def get_identifier():
#     data = 'identifier'
#     # Send request
#     s.sendall(data.encode('utf-8'))
#     # Wait for response
#     datastream = s.recv(1024)
#     return datastream.decode('utf-8')

def send_command(cmd, jid=None):
    data = jid + '~' + cmd if jid else cmd
    # Send request
    s.sendall(data.encode('utf-8'))
    # Wait for response
    datastream = s.recv(1024)
    return datastream.decode('utf-8')

# identifier = get_identifier()
# print('You are logged in as client #{}.format(identifier)')
print('Type a Jabber ID to commit an action upon.')
jid = input('slixfeed > ')
if not jid: jid = 'admin'

# TODO if not argument, enter loop.
try:
    while True:
        # print('Enter an action to act upon Jabber ID {}'.format(jid))
        # print('Enter command:')
        # cmd = input('slixfeed #{} ({}) > '.format(identifier, jid))
        cmd = input('slixfeed ({}) > '.format(jid))
        if cmd != '':
            match cmd:
                case 'switch':
                    print('Type a Jabber ID to commit an action upon.')
                    jid = input('slixfeed > ')
                    if not jid: jid = 'admin'
                    cmd = ''
                case 'exit':
                    send_command(cmd, jid)
                    break
                case _:
                    result = send_command(cmd, jid)
                    print(result)
except KeyboardInterrupt as e:
    print(str(e))
    # logger.error(str(e))

print('Disconnecting from IPC interface.')
s.close()
