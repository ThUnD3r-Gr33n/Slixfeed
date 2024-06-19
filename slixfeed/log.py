#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

TODO Rename module to console or print

To use this class, first, instantiate Logger with the name of your module
or class, then call the appropriate logging methods on that instance.

logger = Logger(__name__)
logger.debug('This is a debug message')

"""

from datetime import datetime
import logging


class Logger:


    def __init__(self, name):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.WARNING) # DEBUG

        ch = logging.StreamHandler()
        ch.setLevel(logging.WARNING)
        
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(name)s: %(message)s')
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

    # def check_difference(function_name, difference):
    #     if difference > 1:
    #         Logger.warning(message)


class Message:


    def printer(text):
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        print('{} {}'.format(current_time, text), end='\r')
