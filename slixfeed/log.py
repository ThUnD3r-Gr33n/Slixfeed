#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

To use this class, first, instantiate Logger with the name of your module
or class, then call the appropriate logging methods on that instance.

logger = Logger(__name__)
logger.debug('This is a debug message')

"""

import logging

class Logger:

    def __init__(self, name):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
    
        self.logger.addHandler(ch)
    
    def critical(self, message):
        self.logger.critical(message)
    
    def debug(self, message):
        self.logger.debug(message)
    
    def error(self, message):
        self.logger.error(message)
    
    def info(self, message):
        self.logger.info(message)
    
    def warning(self, message):
        self.logger.warning(message)
