#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Linux.Networks.Fibrechannel import Fibrechannel
except ImportError:
    Fibrechannel = None


class TestInventoryLinuxNetworksFibrechannel(unittest.TestCase):
    
    @unittest.skipIf(Fibrechannel is None, "Fibrechannel not implemented")
    def test_inventory_linux_networks_fibrechannel(self):
        """Test inventory linux networks fibrechannel"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
