#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (C) 2011 Dominic van Berkel - dominic@baudvine.net
# See LICENSE for details

import sys
import json
import termios


fd = sys.stdin.fileno()
oldattr = termios.tcgetattr(fd)
newattr = oldattr
newattr[3] = newattr[3] & ~termios.ECHO
termios.tcsetattr(fd, termios.TCSANOW, newattr)

print(json.dumps({'target': 'core',
                  'type': 'loaded'}))
while True:
    line = sys.stdin.readline()
    if line.strip() != '':
        #print(json.dumps({'type': 'log',
        #                  'level': 'debug',
        #                  'content': 'received a line:'+line}))
        msgobj = json.loads(line)
        if msgobj['source'] == 'irc' and msgobj['type'] == 'trigger' and msgobj['command'] == 'quit':
            print(json.dumps({'target': 'core',
                              'type': 'quit'}))
    
