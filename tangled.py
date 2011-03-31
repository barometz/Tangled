#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (C) 2011 Dominic van Berkel - dominic@baudvine.net
# See LICENSE for details

# library imports
import json
import logging
import os

from optparse import OptionParser

# twisted imports
from twisted.internet import protocol, reactor

# project-specific imports
from nodes import coreinterface

DEBUG = 0

   
class TangledRouter():
    """The core element of this whole shebang."""
    
    # dict of (shortname, objectref) for loaded instances of
    # TangledProcess
    nodes = {}
    loadingnodes = {}

    # config defaults
    config = {
        'loglevel': 'info',
        'logfilelevel': 'info',
        'logformat': '%(asctime)s %(levelname)-8s %(name)s: %(message)s',
        'datefmt': '%Y-%m-%d %H:%M:%S'
        }

    loglevels = {
        'all': 5,
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
        }


    def __init__(self, config):
        """config: relative path to config file"""
        alive = True
        self.loadconfig(config)
        if DEBUG > 0:
            alive = self.checkconfig()
        if alive:
            self.startlogging()
            self.initnodes()
            reactor.run()
        
    def initnodes(self):
        """Initialize the startup nodes."""
        newnodes = self.config["nodes"]
        newpynodes = self.config["pynodes"]
        logging.info('Loading initial nodes: {}'.format(newnodes))
        logging.info('Loading initial python nodes: {}'.format(newpynodes))
        for node in newnodes:
            if node is not '':
                self.runnode(node)
        for node in newpynodes:
            self.runnode(node, True)
    
    def runnode(self, node, pynode=False):
        """Run a node and stick it in self.nodes
        
        node: string, shortname of a node.
        """
        if pynode:
            process = coreinterface.PythonNode(node, self)
        else:
            process = coreinterface.ExecutableNode(node, self)
        process.spawn()
        self.loadingnodes[node] = process

    def loadconfig(self, filename):
        conf = open(filename, "r")
        self.config.update(json.load(conf))

    def checkconfig(self):
        """Check the configured options against a list of functions to
        validate them""" 
        validconfig = {
            'loglevel': lambda s: s in self.loglevels,
            'logfilelevel': lambda s: s in self.loglevels,
            'nodes': lambda s: isinstance(s, list),
            'pynodes': lambda s: isinstance(s, list)
            }
        alive = True
        for key in self.config: 
            if (key in validconfig and 
                not validconfig[key](self.config[key])):
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
        logging.basicConfig(level=self.loglevels[loglevel],
                            format=self.config['logformat'],
                            datefmt='%H:%M:%S')
        logging.addLevelName(5, 'ALL')
        # now define a logging handler for stdout
        logfile = logging.FileHandler('tangled.log')
        logfile.setLevel(self.loglevels[logfilelevel])
        formatter = logging.Formatter(self.config['logformat'], 
                                      self.config['datefmt'])
        logfile.setFormatter(formatter)
        logging.getLogger('').addHandler(logfile)
        logging.info('New logging session at level {}'.format(loglevel))

    ## Sorta-callbacks for the nodes
    
    def node_loaded(self, node):
        """A node reports that it has finished loading.

        Add it to self.nodes and go through module_loaded hooks
        """
        del self.loadingnodes[node.shortname]
        self.nodes[node.shortname] = node
        logging.info('Node "{}" loaded'.format(node.shortname))


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
