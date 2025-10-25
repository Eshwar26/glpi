#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Aix.Sounds import Sounds
except ImportError:
    Sounds = None


class TestInventoryAixSounds(unittest.TestCase):
    
    @unittest.skipIf(Sounds is None, "Sounds not implemented")
    def test_inventory_aix_sounds(self):
        """Test inventory aix sounds"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
