#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (C) 2011 Dominic van Berkel - dominic@baudvine.net
# See LICENSE for details

import sys
import json

print(json.dumps({'target': 'core',
                  'type': 'loaded'}))

for line in sys.stdin:
    msgobj = json.loads(line)
    if msgobj['source'] == 'irc' and msgobj['type'] == 'trigger' and msgobj['command'] == 'quit':
        print(json.dumps({'target': 'irc',
                          'type': 'quit'}))
    
