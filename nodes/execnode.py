#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (C) 2011 Dominic van Berkel - dominic@baudvine.net
# See LICENSE for details

"""execnode.py

Importable by executable nodes that are written in Python, this little module
contains a number of utility functions that pretty much every node will want
to use.
"""

import sys
import json
import os

def uniqueid():
    """Generator for unique request IDs, only for use within this module"""
    n = 1
    while True: 
        yield n 
        n += 1

rid = uniqueid()

def send(msgobjindict=None, **msgobj):
    """Send a json-serialized msgobj over stdout to the core

    Takes either a dictionary or arbitrary keyword arguments. Attaches a
    unique request id in the 'rid' field and returns that.
    """
    if msgobjindict is not None:
        msgobj = msgobjindict
    if not 'rid' in msgobj:
        # don't change the rid when it's a response
        msgobj['rid'] = rid.next()
    print(json.dumps(msgobj))
    return msgobj['rid']

def log(level, msg):
    """Log a message to the core.  

    'level' is an integer between 0 and 50 inclusive.
    """
    send({'type': 'log',
         'level': level,
         'content': msg})

def startup(initreqs=[]):
    """Start the interface with the core.  Called when the module is done
    loading and can receive stuff.

    Two things: disable "echo" on our stdin to prevent echoin everything we
    receive right back at the core.  Then we can tell the core we're loaded
    and ready.

    initreqs is a list of information the node would like to get from the core
    right now.
    """
    os.system("stty -echo")
    send({'target': 'core',
          'type': 'loaded',
          'initreqs': initreqs})

def getmsg():
    """Get the next line from the core.

    Blocks until a line has been received.  If the line isn't empty and parses
    as json, a msgobj is returned.  Otherwise loop back and get another line.
    """
    while True:
        line = sys.stdin.readline()
        if line.strip() != '':
            try:
                msgobj = json.loads(line)
                return msgobj
            except ValueError:
                log('error', 'Not a json string: {}'.format(line))
