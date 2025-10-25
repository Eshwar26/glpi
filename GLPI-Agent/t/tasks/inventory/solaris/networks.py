#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Solaris.Networks import Networks
except ImportError:
    Networks = None


class TestInventorySolarisNetworks(unittest.TestCase):
    
    @unittest.skipIf(Networks is None, "Networks not implemented")
    def test_inventory_solaris_networks(self):
        """Test inventory solaris networks"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
