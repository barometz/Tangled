# -*- coding: utf-8 -*-

# Copyright (C) 2011 Dominic van Berkel - dominic@baudvine.net
# See LICENSE for details

class TangledInterface():
    """An instance of this is created by Tangled to talk to the node"""

    def __init__(self, router):
        """You'll want to override this to get your module started"""
        self.router = router

    def send(self, msgobj):
        """Send a message to the router"""
        self.router.processObject(msgobj)

    def set_client(self, client):
        self.client = client

    def message(self, msgobj):
        """Received a message from the router.  Pass it on!"""
        self.client.message(msgobj)
        
    def log(self, level, message):
        """Log a message via the router's system.
        
        level is an integer between 0 and 50 inclusive.
        """
        self.send({
                'target': 'core',
                'type': 'log',
                'level': level,
                'message': message
                })

    def unload(self):
        self.send({'type': 'unloaded',
                             'target': 'core'})

    def loaded(self):
        """Node reports that it's finished initial loading.  Tell the core!"""
        self.send({
                'target': 'core',
                'type': 'loaded'
                })

if __name__ == '__main__':
    print "This module is intended for use with Tangled and does not do"
    print "anything useful without it at the moment."
