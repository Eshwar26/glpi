#!/usr/bin/env python3
"""Test Agent - Mock agent for testing"""

import sys
import tempfile
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'lib'))

try:
    from GLPI.Agent import Agent
except ImportError:
    # If GLPI.Agent doesn't exist yet, create a minimal base
    class Agent:
        pass


class TestAgent(Agent):
    """Test agent with temporary directories for testing"""
    
    def __init__(self):
        # Create temporary directory for vardir
        self._vardir_obj = tempfile.TemporaryDirectory()
        self.vardir = self._vardir_obj.name
        
        self.status = 'ok'
        self.targets = []
        self.config = {
            'vardir': self.vardir
        }
    
    def __del__(self):
        # Cleanup temporary directory
        if hasattr(self, '_vardir_obj'):
            try:
                self._vardir_obj.cleanup()
            except:
                pass
