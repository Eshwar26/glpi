#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Macos.Networks import Networks
except ImportError:
    Networks = None


class TestInventoryMacosNetworks(unittest.TestCase):
    
    @unittest.skipIf(Networks is None, "Networks not implemented")
    def test_inventory_macos_networks(self):
        """Test inventory macos networks"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
