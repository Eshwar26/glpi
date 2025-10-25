#!/usr/bin/env python3
"""Test Logger Backend - Mock logger for testing"""

import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / 'lib'))

try:
    from GLPI.Agent.Logger import LoggerBackend
except ImportError:
    # If doesn't exist, create minimal base
    class LoggerBackend:
        pass


class TestLoggerBackend(LoggerBackend):
    """Test logger backend that stores messages for inspection"""
    
    test = True
    
    def __init__(self, params=None):
        self.message = None
        self.level = None
        self.messages = []
    
    def addMessage(self, message=None, level=None, **params):
        """Add a message to the logger"""
        self.message = message or params.get('message')
        self.level = level or params.get('level')
        
        # Store all messages for later inspection
        self.messages.append({
            'message': self.message,
            'level': self.level
        })
