#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (C) 2011 Dominic van Berkel - dominic@baudvine.net
# See LICENSE for details

import execnode

pending = {}
pendingcounter = 0

def handler(msgobj, state):
    if msgobj['source'] == 'irc' and msgobj['type'] == 'trigger':
        if msgobj['command'] == 'quit':
            reqid = state['pendingcounter']
            state['pendingcounter'] += 1
            execnode.send({'target': 'auth',
                           'type': 'haslevel',
                           'nick': msgobj['nick'],
                           'level': 30,
                           'id': reqid})
            state['pending'][reqid] = {'target': 'core',
                                         'type': 'quit'}
    elif msgobj['source'] == 'core':
        if msgobj['type'] == 'quit':
            execnode.send({'target': 'core',
                           'type': 'unloaded'})
            return False
    elif msgobj['source'] == 'auth':
        if msgobj['type'] == 'haslevel':
            if msgobj['result'] == 'true':
                execnode.send(state['pending'][msgobj['id']])
            del state['pending'][msgobj['id']]
    return True

state = {'pending': {},
         'pendingcounter': 0}
execnode.startup()
execnode.loop(handler, state)
