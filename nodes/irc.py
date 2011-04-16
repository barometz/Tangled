#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (C) 2011 Dominic van Berkel - dominic@baudvine.net
# See LICENSE for details

# system imports
import json
import threading
import logging

# twisted imports
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol

# the interface to talk to the core
from nodes import nodeinterface


class Interface(nodeinterface.TangledInterface):
    """Interface to the router, customized for this node"""
    def __init__(self, router):
        nodeinterface.TangledInterface.__init__(self, router)
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

    # please don't touch these without using the relevant locks, self.IRCLock
    # and self.tangledLock
    # requests that need a response from IRC to resolve
    # requests that take an extra argument or otherwise are dicts
    pendingIRCRequests = {'realname': {},
                          'nodes': []}
    # requests that need a response from the rest of the bot to resolve
    pendingTangledRequests = {'nodes': []}

    triggerHooks = {}

    def connectionMade(self):
        """De-facto init function"""
        self.tangledLock = threading.RLock()
        self.IRCLock = threading.RLock()
        self.triggerLock = threading.RLock()
        self.interface = self.factory.interface
        self.interface.set_client(self)
        self.loadconfig()
        irc.IRCClient.connectionMade(self)
        self.interface.loaded()
        self.interface.log(logging.INFO, 'Connected to IRCd')

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)

    def lineReceived(self, line):
        self.interface.log(5, '< {}'.format(line))
        irc.IRCClient.lineReceived(self, line)

    def sendLine(self, line):
        """Overridden to make sure all strings are encoded properly before
        they're sent out"""
        line = line.encode(self.encoding)
        self.interface.log(5, '> {}'.format(line))
        irc.IRCClient.sendLine(self, line)

    def loadconfig(self):
        self.config = self.factory.config
        # I could do this in a loop with setattr but I feel this is safer in
        # case of errors.
        self.nickname = self.config['nickname']
        self.realname = self.config['realname']
        self.lineRate = self.config['lineRate']
        self.password = self.config['password']
        self.triggerChar = self.config['triggerChar']
        self.encoding = self.config['encoding']

    ## Callbacks from irc.IRCClient

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
            
    def action(self, user, channel, msg):
        """This will get called when the bot sees someone do an action."""
        user = user.split('!', 1)[0]

    ## "Raw" IRCClient callbacks 

    def irc_NICK(self, prefix, params):
        """Called when an IRC user changes their nickname."""
        old_nick = prefix.split('!')[0]
        new_nick = params[0]

    def irc_RPL_WHOISUSER(self, prefix, params):
        """Part of a WHOIS reply.

        After the bot's nickname params contains the following in this order:
        nickname, username, host(mask), '*', realname
        """
        with self.IRCLock:
            if params[1] in self.pendingIRCRequests['realname']:
                for callback in self.pendingIRCRequests['realname'][params[1]]:
                    callback(params[-1])
                del self.pendingIRCRequests['realname'][params[1]]
    
    ## Own callbacks

    def triggerMessage(self, nick, channel, msg):
        ## split msg into [command, arguments]
        msg = msg[1:].split(None, 1)
        handler = getattr(self, 'trigger_{}'.format(msg[0]), None)
        if handler is not None:
            handler(nick, channel, msg)
        elif msg[0] in self.triggerHooks:
            for node in self.triggerHooks[msg[0]]:
                self.interface.send(
                    {'target': node,
                     'type': 'trigger',
                     'content': msg,
                     'nick': nick,
                     'channel': channel})

#    def trigger_quit(self, nick, channel, msg):
#        self.interface.send({'target': 'control.py',
#                             'type': 'trigger',
#                             'command': 'quit',
#                             'nick': nick})
                            
    def trigger_nodes(self, nick, channel, msg):
        self.interface.send({'target': 'core', 
                             'type': 'nodes', 
                             'nick': nick,
                             'channel': channel})

    def trigger_whois(self, nick, channel, msg):
        if len(msg) != 2:
            self.msg(channel, 
                     '{}: You need to tell me who to whois!'.format(nick))
            return
        send = lambda result: \
            self.msg(channel, "{}'s name is {}".format(msg[1], result))
        with self.IRCLock:
            if msg[1] in self.pendingIRCRequests['realname']:
                self.pendingIRCRequests['realname'][msg[1]].append(send)
            else:
                self.pendingIRCRequests['realname'][msg[1]] = [send]
        self.whois(msg[1])

    ## Handling messages from the core

    def message(self, msgobj):
        """Received a message from the core."""
        method = getattr(self, 'tangled_{type}'.format(**msgobj), 
                         self.unhandled)
        method(msgobj)

    def unhandled(self, msgobj):
        """Called when a message is received with a type I don't have a handler
        for."""
        self.interface.log(logging.WARNING, 
                           "Received unhandled message type '{type}' from node \
'{source}'".format(**msgobj))

    def tangled_addhook(self, msgobj):
        if 'trigger' in msgobj:
            with self.triggerLock:
                if msgobj['trigger'] in self.triggerHooks:
                    self.triggerHooks[msgobj['trigger']].append(
                        msgobj['source'])
                else:
                    self.triggerHooks[msgobj['trigger']] = \
                                          [msgobj['source']]

    def tangled_nodes(self, msgobj):
        nodes = ' '.join(msgobj['content'])
        self.msg(msgobj['channel'], '{}: {}'.format(msgobj['nick'], nodes))

    def tangled_quit(self, msgobj):
        if msgobj['source'] == 'core':
            self.quit("Thanks for all the fish!")


class TangledFactory(protocol.ClientFactory):
    """A factory for Tangled.  The irc node, anyway.

    A new protocol instance will be created each time we connect to the server.
    """

    # the class of the protocol to build when new connection is made
    protocol = IRCThing
    
    config = {
        'nickname': 'tangled',
        'realname': 'Thomas A.N. Gled',
        'lineRate': 1,
        'triggerChar': '!',
        'encoding': 'utf-8'
        }

    def __init__(self, interface):
        self.interface = interface
        self.loadconfig()

    def loadconfig(self):
        # strictly speaking this path shouldn't be hardcoded.  Really bad form
        # for a python module.
        confp = open('nodes/conf/irc.json', 'r')
        self.config.update(json.load(confp))

    def clientConnectionLost(self, connector, reason):
        """If we get disconnected, reconnect to server."""
        self.interface.unload()

    def clientConnectionFailed(self, connector, reason):
        self.interface.log(logging.CRITICAL, 'Connection failed: {}'.format(reason))
        reactor.stop()

if __name__ == '__main__':
    print 'This node is intended for use with Tangled and does not do'
    print 'anything useful without it at the moment.'
