#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (C) 2011 Dominic van Berkel - dominic@baudvine.net
# See LICENSE for details

import sys
import execnode

pending = {}
pendingcounter = 0

execnode.startup(["nodes"])

# This node depends on the irc node, so for clarity's sake we'll first wait
# for that to have loaded.
while True:
    msgobj = execnode.getmsg()
    if msgobj['type'] == 'nodes':
        if 'irc' in msgobj['content']:
            break
        else:
            execnode.send({'target': 'core',
                           'type': 'addhooks',
                           'hooks': ['node_loaded']})
    elif msgobj['type'] == 'node_loaded' and msgobj['node'] == 'irc':
                break
    elif msgobj['source'] == 'core' and msgobj['type'] == 'quit':
        execnode.send({'target': 'core',
                       'type': 'unloaded'})
        sys.exit()

# The IRC module has been loaded
# install !quit hook
execnode.send({'target': 'irc',
               'type': 'addhook',
               'trigger': 'quit'})

while True:
    msgobj = execnode.getmsg()
    if msgobj['source'] == 'irc' and msgobj['type'] == 'trigger':
        if msgobj['content'][0] == 'quit':
            reqid = pendingcounter
            pendingcounter += 1
            execnode.send({'target': 'auth.py',
                           'type': 'haslevel',
                           'nick': msgobj['nick'],
                           'level': 30,
                           'id': reqid})
            pending[reqid] = {'target': 'core',
                              'type': 'quit'}
    elif msgobj['source'] == 'core':
        if msgobj['type'] == 'quit':
            execnode.send({'target': 'core',
                           'type': 'unloaded'})
            break
        elif msgobj['type'] == 'nodes':
            if 'irc' in msgobj['content']:
                # install !quit hook
                execnode.send({'target': 'irc',
                               'type': 'addhook',
                               'trigger': 'quit'})
    elif msgobj['source'] == 'auth.py':
        if msgobj['type'] == 'haslevel':
            if msgobj['result'] == 'true':
                execnode.send(pending[msgobj['id']])
                del pending[msgobj['id']]
