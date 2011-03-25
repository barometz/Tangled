# -*- coding: utf-8 -*-

class TangledInterface():
    """An instance of this is created by Tangled to talk to the module."""

    def __init__(self, router):
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
        
        level is one of all,debug,info,warning,error,critical
        """
        self.send({
                'target': 'core',
                'type': 'log',
                'level': level,
                'message': message
                })

if __name__ == '__main__':
    print "This module is intended for use with Tangled and does not do"
    print "anything useful without it at the moment."
