#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (C) 2011 Dominic van Berkel - dominic@baudvine.net
# See LICENSE for details

import sys
import json
import os


def send(msgobj):
    print(json.dumps(msgobj))

def log(level, msg):
    send({'type': 'log',
         'level': level,
         'content': msg})

def startup():
    """Start the interface with the core.  Called when the module is done
    loading and can receive stuff.

    Two things: disable "echo" on the stdin pipe we're talking to - otherwise
    everything the module says is looped back on our own input, which is
    messy.  Then we can tell the core we're loaded and ready.
    """
    os.system("stty -echo")
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
