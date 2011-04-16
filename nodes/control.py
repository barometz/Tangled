#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (C) 2011 Dominic van Berkel - dominic@baudvine.net
# See LICENSE for details

import execnode

pending = {}
pendingcounter = 0

execnode.startup()
while True:
    msgobj = execnode.getmsg()
    if msgobj:
        if msgobj['source'] == 'irc' and msgobj['type'] == 'trigger':
            if msgobj['command'] == 'quit':
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
        elif msgobj['source'] == 'auth.py':
            if msgobj['type'] == 'haslevel':
                if msgobj['result'] == 'true':
                    execnode.send(pending[msgobj['id']])
                del pending[msgobj['id']]
