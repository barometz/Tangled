#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (C) 2011 Dominic van Berkel - dominic@baudvine.net
# See LICENSE for details

import sys
import json
import termios


def send(msgobj):
    print(json.dumps(msgobj))

def log(level, msg):
    send({'type': 'log',
         'level': level,
         'content': msg})

def startup():
    # turn off echoing of stdin to avoid nasty loops.
    fd = sys.stdin.fileno()
    oldattr = termios.tcgetattr(fd)
    newattr = oldattr
    newattr[3] = newattr[3] & ~termios.ECHO 
    termios.tcsetattr(fd, termios.TCSANOW, newattr)
    send({'target': 'core',
          'type': 'loaded'})

def getmsg():
    line = sys.stdin.readline()
    if line.strip() == '':
        msgobj = False
    else:
        try:
            msgobj = json.loads(line)
        except ValueError:
            log('error', 'Not a json string: {}'.format(line))
            msgobj = False
    return msgobj
