#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (C) 2011 Dominic van Berkel - dominic@baudvine.net
# See LICENSE for details

# the interface to talk to the core
from modules import interface

# twisted imports
from twisted.words.protocols import irc
from twisted.protocols import basic
from twisted.internet import reactor, protocol, stdio
from twisted.python import log

# system imports
import json

class Interface(interface.TangledInterface):
    """Interface to the router, customized for this module"""

    def __init__(self, router):
        interface.TangledInterface.__init__(self, router)
        # create factory protocol and application
        f = TangledFactory(self)

        # connect factory to this host and port
        server = f.config['server']
        port = f.config['port']
        reactor.connectTCP(server, port, f)

class IRCThing(irc.IRCClient):
    """This fellow handles the IRC side of the communication."""
    
    sourceURL = 'http://nazgjunk.users.anapnea.net/tangled/'
    versionName = 'Tangled'
    versionNum = '0.0'

    pendingIRCRequests = {'realname': {},
                          'modules': []}

    def sendLine(self, line):
        """Overridden to make sure all strings are encoded properly before
        they're sent out"""
        line = line.encode('utf-8')
        self.interface.log('all', '> {}'.format(line))
        irc.IRCClient.sendLine(self, line)

    def connectionMade(self):
        self.interface = self.factory.interface
        self.interface.set_client(self)
        self.loadconfig()
        irc.IRCClient.connectionMade(self)
        self.interface.log('info', 'Connected to IRCd')

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)

    def loadconfig(self):
        self.config = self.factory.config
        self.nickname = self.config['nickname']
        self.realname = self.config['realname']
        self.lineRate = self.config['lineRate']
        self.password = self.config['password']
        self.triggerChar = self.config['triggerChar']

    # callbacks for events

    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        for channel in self.config['channels']:
            self.join(channel)

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        pass

    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""
        msg = msg.strip()
        nick = user.split('!', 1)[0]

        if msg.startswith(self.triggerChar) and len(msg) > 1:
            self.triggerMessage(nick, channel, msg)
            
        # Otherwise check to see if it is a message directed at me
        if msg.startswith(self.nickname + ":"):
            msg = '{}: I am a log bot'.format(nick)
            self.msg(channel, msg)

    def action(self, user, channel, msg):
        """This will get called when the bot sees someone do an action."""
        user = user.split('!', 1)[0]
        
    def triggerMessage(self, nick, channel, msg):
        ## split msg into [command, arguments]
        msg = msg[1:].split(None, 1)
        handler = getattr(self, 'trigger_{}'.format(msg[0]), None)
        if handler is not None:
            handler(nick, channel, msg)
        #else: go through !trigger hooks

    def trigger_modules(self, nick, channel, msg):
        self.interface.send({'target': 'core', 
                             'type': 'modules', 
                             'nick': nick,
                             'channel': channel})

    def trigger_whois(self, nick, channel, msg):
        if len(msg) != 2:
            self.msg(channel, 
                     '{}: You need to tell me who to whois!'.format(nick))
            return
        send = lambda result: self.msg(channel, 
                                         "{}'s name is {}".format(msg[1], 
                                                                  result))
        if msg[1] in self.pendingIRCRequests['realname']:
            self.pendingIRCRequests['realname'][msg[1]].append(send)
        else:
            self.pendingIRCRequests['realname'][msg[1]] = [send]
        self.whois(msg[1])

    # irc callbacks

    def irc_NICK(self, prefix, params):
        """Called when an IRC user changes their nickname."""
        old_nick = prefix.split('!')[0]
        new_nick = params[0]

    def irc_RPL_WHOISUSER(self, prefix, params):
        """Part of a WHOIS reply.

        After the bot's nickname params contains the following in this order:
        nickname, username, host(mask), '*', realname
        """
        if params[1] in self.pendingIRCRequests['realname']:
            for callback in self.pendingIRCRequests['realname'][params[1]]:
                callback(params[-1])
            del self.pendingIRCRequests['realname'][params[1]]

    def lineReceived(self, line):
        self.interface.log('all', '< {}'.format(line))
        irc.IRCClient.lineReceived(self, line)
    
    ### module comms
    def message(self, msgobj):
            method = getattr(self, 'msg_{}'.format(msgobj['type']), 
                             self.unhandled)
            method(msgobj)

    def unhandled(self, msgobj):
        """Called when a message is received with a type I don't have a handler
        for."""
        self.interface.log('warning', 
                           "Received unhandled message type '{}' from module \
'{}'".format(msgobj['type'], msgobj['source']))

    def msg_modules(self, msgobj):
        ## need some stuff to keep track of pending requests etc
        modules = ' '.join(msgobj['content'])
        self.msg(msgobj['channel'], '{}: {}'.format(msgobj['nick'], modules))


class TangledFactory(protocol.ClientFactory):
    """A factory for Tangled.  The irc module, anyway.

    A new protocol instance will be created each time we connect to the server.
    """

    # the class of the protocol to build when new connection is made
    protocol = IRCThing

    
    config = {
        'nickname': 'tangled',
        'realname': 'Thomas A.N. Gled',
        'lineRate': 1,
        'triggerChar': '!'
        }

    def __init__(self, interface):
        self.interface = interface
        self.loadconfig()

    def loadconfig(self):
        confp = open('modules/conf/irc.json', 'r')
        self.config.update(json.load(confp))

    def clientConnectionLost(self, connector, reason):
        """If we get disconnected, reconnect to server."""
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        self.interface.log('critical', 'Connection failed: {}'.format(reason))
        reactor.stop()


if __name__ == '__main__':
    print 'This module is intended for use with Tangled and does not do'
    print 'anything useful without it at the moment.'
