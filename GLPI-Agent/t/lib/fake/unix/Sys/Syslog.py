#!/usr/bin/env python3
"""Sys::Syslog fake module for Windows platforms"""

# Log level constants
LOG_ERR = 3
LOG_WARNING = 4
LOG_INFO = 6
LOG_DEBUG = 7


def syslog(*args, **kwargs):
    """Mock syslog function - no-op"""
    pass


def openlog(*args, **kwargs):
    """Mock openlog function - no-op"""
    pass


def closelog():
    """Mock closelog function - no-op"""
    pass


__all__ = ['LOG_ERR', 'LOG_WARNING', 'LOG_INFO', 'LOG_DEBUG', 
           'syslog', 'openlog', 'closelog']
