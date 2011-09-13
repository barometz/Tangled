#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (C) 2011 Dominic van Berkel - dominic@baudvine.net
# See LICENSE for details

import execnode

execnode.startup()

stdin = execnode.getinput()

for msgobj in stdin:
    if msgobj['type'] == 'haslevel':
        if msgobj['nick'] == 'nazgjunk':
            msgobj['target'] = msgobj['source']
            msgobj['result'] = 'true'
            execnode.send(msgobj)
        else:
            msgobj['target'] = msgobj['source']
            msgobj['result'] = 'false'
            execnode.send(msgobj)
    elif msgobj['source'] == 'core':
        if msgobj['type'] == 'quit':
            execnode.send(target='core',
                          type='unloaded')
            break
