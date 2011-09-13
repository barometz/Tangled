#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (C) 2011 Dominic van Berkel - dominic@baudvine.net
# See LICENSE for details

import sys
import execnode

execnode.startup(["nodes"])

stdin = execnode.getinput()

# This node depends on the irc node, so for clarity's sake we'll first wait
# for that to have loaded.
for msgobj in stdin:
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
# install !quit and !nodes hooks
execnode.send({'target': 'irc',
               'type': 'addhook',
               'trigger': 'quit'})

execnode.send({'target': 'irc',
               'type': 'addhook',
               'trigger': 'test'})

for msgobj in stdin:
    if msgobj['source'] == 'irc':
        if msgobj['type'] == 'trigger':
            if msgobj['content'][0] == 'test':
                execnode.send({'target': 'irc',
                               'type': 'privmsg',
                               'to': msgobj['channel'],
                               'message': msgobj['nick'] + ': hi!'})
    elif msgobj['source'] == 'core':
        if msgobj['type'] == 'quit':
            execnode.send({'target': 'core',
                           'type': 'unloaded'})
            break
