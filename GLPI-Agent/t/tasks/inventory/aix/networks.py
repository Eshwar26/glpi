#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Aix.Networks import Networks
except ImportError:
    Networks = None


class TestInventoryAixNetworks(unittest.TestCase):
    
    @unittest.skipIf(Networks is None, "Networks not implemented")
    def test_inventory_aix_networks(self):
        """Test inventory aix networks"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
