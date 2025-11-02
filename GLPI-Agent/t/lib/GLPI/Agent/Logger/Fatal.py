#!/usr/bin/env python3
"""Fatal Logger Backend - Raises exceptions on log messages for testing"""


class Fatal:
    """Logger backend that raises exceptions when messages are logged"""
    
    def __init__(self, params=None):
        """
        Initialize fatal logger backend.
        
        Args:
            params: Optional parameters (unused)
        """
        pass
    
    def addMessage(self, message=None, **kwargs):
        """
        Add a message by raising an exception.
        
        Args:
            message: The message to raise as exception
            **kwargs: Additional parameters (unused)
            
        Raises:
            Exception: Always raises with the message
        """
        msg = message if message else kwargs.get('message', 'Fatal logger called')
        raise Exception(msg)
