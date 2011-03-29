# -*- coding: utf-8 -*-

# Copyright (C) 2011 Dominic van Berkel - dominic@baudvine.net
# See LICENSE for details

import json
import logging

from twisted.internet import protocol, reactor


class TangledNode():
    """Abstract class defining the interface for Tangled nodes."""
    def __init__(self, shortname, router):
        self.shortname = shortname
        self.router = router
        self.startlogging()

    def processObject(self, msgobj):
        if 'type' in msgobj and msgobj['type'] != 'log':
            self.logger.debug('Received: {}'.format(json.dumps(msgobj)))
        msgobj['source'] = self.shortname
        if 'target' in msgobj and msgobj['target'] in self.router.nodes:
            self.router.nodes[msgobj['target']].message(msgobj)         
        elif msgobj['target'] == 'core': 
            self.coreMessage(msgobj)

    def startlogging(self):
        """Create a node-specific logger object"""
        self.logger = logging.getLogger(self.shortname)    

    def sendCoreMessage(self, msgobj):
        """Send a message from core to the attached node """
        msgobj.update({'source': 'core',
                       'target': self.shortname})
        self.message(msgobj)

    def coreMessage(self, msgobj):
        """Called when a node sends a message to 'core'"""
        method = getattr(self, 'msg_{}'.format(msgobj['type']))
        method(msgobj)

    ## Callbacks for messages from the node

    def msg_log(self, msgobj):
        """Log a message. 

        Expected keys:
        level: integer between 0 and 50 inclusive.
        message: string
        """
        if 'message' in msgobj:
            message = msgobj['message']
            if 'level' in msgobj and (0 <= msgobj['level'] <= 50):
                level = msgobj['level']
            else:
                level = logging.INFO
            self.logger.log(level, message)

    def msg_nodes(self, msgobj):
        """A node might want to know what nodes have been loaded, for
        instance to enable or disable certain functionality.

        No other keys expected.
        """
        nodes_list = self.router.nodes.keys()
        # update to preserve other keys the node might have attached for
        # reference purposes
        msgobj.update({'type': 'nodes',
                       'content': nodes_list})
        self.sendCoreMessage(msgobj)

    ### Some functions that the subclass /really/ needs to implement.

    def spawn(self):
        """Run the actual node."""
        raise NotImplementedError

    def message(self, msgobj):
        """Send a message to the node"""
        raise NotImplementedError


class PythonNode(TangledNode):
    """Router-side interface for importable python nodes.

    The main function that is exposed to the router is message(), taking
    one argument: a dict that the node at the other end can do something
    useful with.
    """
    def spawn(self):
        pynode = __import__('nodes.{}'.format(self.shortname), globals())
        # because __import__ returns 'nodes' here:
        pynode = getattr(pynode, self.shortname)
        self.interface = pynode.Interface(self)

    def message(self, msgobj):
        """Another node has sent this one a message.  Pass it on!"""
        self.interface.message(msgobj)
        # conditional to save a tiny bit on json overhead
        self.logger.debug('Sent: {}'.format(json.dumps(msgobj)))


class ExecutableNode(TangledNode, protocol.ProcessProtocol):
    """Router-side interface for executable (stdio-based) nodes"""
    _buffer=''
    delimiter = '\r\n'
    MAX_LENGTH = 16384
    
    def spawn(self):
        reactor.spawnProcess(self, 'nodes/'+self.shortname, [self.shortname], 
                             env=os.environ, usePTY=True)
    
    def message(self, msgobj):
        msgstring = json.dumps(msgobj)
        self._sendLine(msgstring)
        self.logger.debug("Sent: {}".format(msgstring))

    ## ProcessProtocol overrides

    def _sendLine(self, line):
        """Sends a line of text to the node.

        line shouldn't end with a newline, we'll tack that on here.
        No line rate limiting implemented as I hope we don't have to
        worry about flooding the system's IO capabilities.

        """
        self.logger.log(5, 'Sent: {}'.format(line))
        return self.transport.write(line+self.delimiter)

    ## ProcessProtocol callbacks

    def connectionMade(self):
        self.logger.debug('Stdio pipe connected')

    def outReceived(self, data):
        """Called for received data.
        
        Incoming data is split into lines, anything that's left over
        is put in _buffer for later use. self.lineReceived is called
        for every line. Large portions of code nicked from Twisted's
        LineReceiver.

        """
        self._buffer = self._buffer+data
        while True:
            try:
                # Split lines.  If there's no linebreak yet,
                # ValueError is thrown, _buffer remains as it was
                # and we'll try again on the next call.
                line, self._buffer = self._buffer.split(self.delimiter, 1)
            except ValueError:
                if len(self._buffer) > self.MAX_LENGTH:
                    line, self._buffer = self._buffer, ''
                    return self.lineLengthExceeded(line)
                break
            else:
                linelength = len(line)
                if linelength > self.MAX_LENGTH:
                    # this line is getting pretty long let's ditch it
                    exceeded = line + self._buffer
                    self._buffer = ''
                    return self.lineLengthExceeded(exceeded)
                why = self.lineReceived(line)
                if why or self.transport and self.transport.disconnecting:
                    return why
        else:
            data=self.__buffer
            self.__buffer=''
            if data:
                return self.rawDataReceived(data)

    def lineReceived(self, line):
        """Process the received lines. (from the node)

        Figures out where a line should go and transmogrifies it to
        the right format. Then sends it where it should go.

        """
        msgobj = json.loads(line)
        self.processObject(msgobj)

    def lineLengthExceeded(self, line): 
        """Called when the maximum line length is exceeded.

        The LineReceiver implementation just kills the connection,
        we might want to be a little more subtle about it.

        """
        self.logger.warning(
            "Maximum line length ({}) exceeded.".format(MAX_LENGTH))
