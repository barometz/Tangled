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
# install !quit and !nodes hooks
execnode.send({'target': 'irc',
               'type': 'addhook',
               'trigger': 'quit'})

execnode.send({'target': 'irc',
               'type': 'addhook',
               'trigger': 'nodes'})

execnode.send({'target': 'irc',
               'type': 'addhook',
               'trigger': 'load'})

while True:
    msgobj = execnode.getmsg()
    if msgobj['source'] == 'irc':
        if msgobj['type'] == 'trigger':
            if msgobj['content'][0] == 'nodes':
                # hm. maybe wrap these next four statements in a function.
                reqid = execnode.send({'target': 'core',
                                       'type': 'nodes'})
                pending[reqid] = {'target': 'irc',
                                  'type': 'privmsg',
                                  'to': msgobj['channel'],
                                  'message': msgobj['nick'] + ': {}'}
            elif msgobj['content'][0] == 'quit':
                reqid = execnode.send({'target': 'auth.py',
                                       'type': 'haslevel',
                                       'nick': msgobj['nick'],
                                       'level': 30})
                pending[reqid] = {'target': 'core',
                                  'type': 'quit'}
            elif msgobj['content'][0] == 'load':
                if len(msgobj['content']) == 2:
                    execnode.send({'target': 'core',
                                   'type': 'loadnode',
                                   'node': msgobj['content'][1],
                                   'pynode': False})
            elif msgobj['content'][0] == 'reload':
                if len(msgobj['content']) == 2:
                    execnode.send({'target': 'core',
                                   'type': 'reloadnode',
                                   'node': msgobj['content'][1]})
    elif msgobj['source'] == 'core':
        if msgobj['type'] == 'quit':
            execnode.send({'target': 'core',
                           'type': 'unloaded'})
            break
        if msgobj['type'] == 'nodes':
            nodes = ' '.join(msgobj['content'])
            pending[msgobj['rid']]['message'] = pending[msgobj['rid']]['message'].format(nodes)
            execnode.send(pending[msgobj['rid']])
            del pending[msgobj['rid']]
    elif msgobj['source'] == 'auth.py':
        if msgobj['type'] == 'haslevel':
            try:
                if msgobj['result'] == 'true':
                    execnode.send(pending[msgobj['rid']])
                del pending[msgobj['rid']]
            except KeyError:
                execnode.log(30, 'Haslevel response from auth.py with unknown pending id')
