#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

import json
import logging
import os

from optparse import OptionParser

from twisted.internet import protocol, reactor


DEBUG = 0
LEVELS = {
    'all': 5, ## for literal messages between router and modules
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL
    }

class PyModProcess(protocol.ProcessProtocol):
    """Router-side interface for importable python modules (pymods).

    The main function that is exposed to the router is message(), taking
    one argument: a dict that the module at the other end can do something
    useful with.
    """
    def __init__(self, shortname, router):
        self.shortname = shortname
        self.router = router
        self.startlogging()

    def startlogging(self):
        """Create a module-specific logger object"""
        self.logger = logging.getLogger(self.shortname)    

    def spawn(self):
        pymod = __import__('modules.{}'.format(self.shortname), globals())
        # because __import__ returns 'modules' here:
        pymod = getattr(pymod, self.shortname)
        self.interface = pymod.Interface(self)

    def processObject(self, msgobj):
        if 'type' in msgobj and msgobj['type'] != 'log':
            self.logger.debug('Received: {}'.format(json.dumps(msgobj)))
        msgobj['source'] = self.shortname
        if 'target' in msgobj and msgobj['target'] in self.router.modules:
            self.router.modules[msgobj['target']].message(msgobj)         
        elif msgobj['target'] == 'core': 
            self.coreMessage(msgobj)

    def message(self, msgobj):
        """Another module has sent this one a message.  Pass it on!"""
        self.interface.message(msgobj)
        # conditional to save a tiny bit on json overhead
        self.logger.debug('Sent: {}'.format(json.dumps(msgobj)))

    ### core <-> module communication

    def sendCoreMessage(self, msgobj):
        """Send a message from core to the attached module """
        msgobj.update({'source': 'core'})
        self.message(msgobj)

    def coreMessage(self, msgobj):
        """Called when a module sends a message to 'core'"""
        method = getattr(self, 'msg_{}'.format(msgobj['type']))
        method(msgobj)

    def msg_log(self, msgobj):
        """Log a message. 

        Expected keys:
        level: string out of all,debug,warning,error,critical
        message: string
        """
        if 'message' in msgobj:
            message = msgobj['message']
            if 'level' in msgobj and msgobj['level'] in LEVELS:
                level = msgobj['level']
            else:
                level = 'info'
            self.logger.log(
                (LEVELS[level] if level in LEVELS else LEVELS['info']), message)

    def msg_modules(self, msgobj):
        """A module might want to know what modules have been loaded, for
        instance to enable or disable certain functionality.

        No other keys expected.
        """
        modules_list = self.router.modules.keys()
        self.sendCoreMessage({ 'type': 'modules', 
                               'content': modules_list })


class ExecutableProcess(PyModProcess):
    """Router-side interface for executable (stdio-based) modules"""
    _buffer=''
    delimiter = '\r\n'
    MAX_LENGTH = 16384
    paused = False
    
    def spawn(self):
        reactor.spawnProcess(self, 'modules/'+self.shortname, [self.shortname], 
                             env=os.environ, usePTY=True)
    
    def _sendLine(self, line):
        """Sends a line of text to the module.

        line shouldn't end with a newline, we'll tack that on here.
        No line rate limiting implemented as I hope we don't have to
        worry about flooding the system's IO capabilities.

        """
        self.logger.log(5, 'Sent: {}'.format(line))
        return self.transport.write(line+self.delimiter)

    def message(self, msgobj):
        msgstring = json.dumps(msgobj)
        self._sendLine(msgstring)
        self.logger.debug("Sent: {}".format(msgstring))

    ### CALLBACKS AND RELATED STUFF

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
        while not self.paused:
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
            if not self.paused:
                data=self.__buffer
                self.__buffer=''
                if data:
                    return self.rawDataReceived(data)

    def lineReceived(self, line):
        """Process the received lines. (from the module)

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

   
class TangledRouter():
    """The core element of this whole shebang."""
    
    # dict of (shortname, objectref) for loaded instances of
    # TangledProcess
    modules = {}

    # config defaults
    config = {
        'loglevel': 'info',
        'logfilelevel': 'info',
        'logformat': '%(asctime)s %(levelname)-8s %(name)s: %(message)s',
        'datefmt': '%Y-%m-%d %H:%M:%S'
        }

    validconfig = {
        'loglevel': lambda s: s in LEVELS,
        'logfilelevel': lambda s: s in LEVELS,
        'modules': lambda s: isinstance(s, list),
        'pymods': lambda s: isinstance(s, list)
        }

    def __init__(self, config):
        """config: relative path to config file"""
        alive = True
        self.loadconfig(config)
        if DEBUG > 0:
            alive = self.checkconfig()
        if alive:
            self.startlogging()
            self.initmodules()
            reactor.run()
        
    def initmodules(self):
        """Initialize the startup modules.
        
        modules: list of executable names.

        """
        newmodules = self.config["modules"]
        newpymodules = self.config["pymods"]
        logging.info('Loading initial modules: {}'.format(newmodules))
        logging.info('Loading initial python modules: {}'.format(newpymodules))
        for module in newmodules:
            if module is not '':
                self.runmodule(module)
        for module in newpymodules:
            self.runmodule(module, True)
        logging.info('Modules loaded: {}'.format(self.modules))
    
    def runmodule(self, module, pymod=False):
        """Run a module and stick it in self.modules"""
        if pymod:
            process = PyModProcess(module, self)
        else:
            process = ExecutableProcess(module, self)
        process.spawn()
        self.modules[module] = process

    def loadconfig(self, filename):
        conf = open(filename, "r")
        self.config.update(json.load(conf))

    def checkconfig(self):
        """Check the configured options against a list of functions to
        validate them""" 
        alive = True
        for key in self.config: 
            if (key in self.validconfig and 
                not self.validconfig[key](self.config[key])):
                logging.critical("Invalid configuration option {}: {}".format(
                        key, self.config[key]))
                alive = False
        return alive

    def startlogging(self):
        """Figure out the log level and start logging"""
        loglevel = self.config['loglevel']
        logfilelevel = self.config['logfilelevel']
        # -v and -vv options only affect stdout logging
        loglevel = (loglevel, 'debug', 'all')[DEBUG]        
        logging.basicConfig(level=LEVELS[loglevel],
                            format=self.config['logformat'],
                            datefmt='%H:%M:%S')
        logging.addLevelName(5, 'ALL')
        # now define a logging handler for stdout
        logfile = logging.FileHandler('tangled.log')
        logfile.setLevel(LEVELS[logfilelevel])
        formatter = logging.Formatter(self.config['logformat'], 
                                      self.config['datefmt'])
        logfile.setFormatter(formatter)
        logging.getLogger('').addHandler(logfile)
        logging.info('New logging session at level {}'.format(loglevel))


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('-v', action='count', dest='verbosity', default=0,
                      help='-v for debug mode, -vv for really verbose debug mode.')
    parser.add_option('-c', action='store', type='string', dest='filename', 
                      default='tangled.json', 
                      help='Location of the config file. Defaults to tangled.json.')
    (options, args) = parser.parse_args()
        
    DEBUG = options.verbosity

    router = TangledRouter(options.filename)
