#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Hpux.Networks import Networks
except ImportError:
    Networks = None


class TestInventoryHpuxNetworks(unittest.TestCase):
    
    @unittest.skipIf(Networks is None, "Networks not implemented")
    def test_inventory_hpux_networks(self):
        """Test inventory hpux networks"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
