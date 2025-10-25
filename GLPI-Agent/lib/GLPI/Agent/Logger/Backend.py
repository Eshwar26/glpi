"""
GLPI::Agent::Logger::Backend - An abstract logger backend

This is an abstract base class for logger backends.
"""

from abc import ABC, abstractmethod


class Backend(ABC):
    """Abstract base class for logger backends."""
    
    test = False
    
    def __init__(self, config=None):
        """
        Initialize the logger backend.
        
        Args:
            config: The agent configuration object
        """
        self.config = config
    
    @abstractmethod
    def add_message(self, level, message):
        """
        Add a log message with a specific level.
        
        Args:
            level (str): Can be one of: debug, info, warning, error
            message (str): The log message
        """
        pass
    
    def reload(self):
        """Used to reload a logger."""
        pass
