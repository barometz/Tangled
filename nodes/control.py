#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (C) 2011 Dominic van Berkel - dominic@baudvine.net
# See LICENSE for details

import execnode

pending = {}
pendingcounter = 0

execnode.startup()

execnode.send({'target': 'core',
               'type': 'addhooks',
               'hooks': ['node_loaded']})

while True:
    msgobj = execnode.getmsg()
    if msgobj:
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
            elif msgobj['type'] == 'node_loaded':
                if msgobj['node'] == 'irc':
                    # install !quit hook
                    execnode.send({'target': 'irc',
                                   'type': 'addhook',
                                   'trigger': 'quit'})
        elif msgobj['source'] == 'auth.py':
            if msgobj['type'] == 'haslevel':
                if msgobj['result'] == 'true':
                    execnode.send(pending[msgobj['id']])
                del pending[msgobj['id']]
