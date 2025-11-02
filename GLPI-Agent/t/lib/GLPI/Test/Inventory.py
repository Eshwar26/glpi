#!/usr/bin/env python3
"""Test Inventory Module - Test inventory class"""

import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'lib'))

try:
    from GLPI.Agent.Inventory import Inventory
    from GLPI.Agent.Config import Config
    from GLPI.Agent.Logger import Logger
except ImportError:
    # Fallback if modules don't exist yet
    class Inventory:
        def __init__(self, **kwargs):
            pass
    
    class Config:
        def __init__(self, **kwargs):
            pass
    
    class Logger:
        def __init__(self, **kwargs):
            pass


class TestInventory(Inventory):
    """Test inventory class with default logger configuration"""
    
    def __init__(self, **params):
        """
        Initialize test inventory with logger configured for testing.
        
        Args:
            **params: Additional parameters passed to parent class
        """
        # Create logger with test configuration
        config = Config(
            options={
                'config': 'none',
                'debug': 2,
                'logger': 'Fatal'
            }
        )
        
        logger = Logger(config=config)
        
        # Initialize parent with logger
        super().__init__(logger=logger, **params)
