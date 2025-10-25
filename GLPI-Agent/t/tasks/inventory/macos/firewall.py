#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Macos.Firewall import Firewall
except ImportError:
    Firewall = None


class TestInventoryMacosFirewall(unittest.TestCase):
    
    @unittest.skipIf(Firewall is None, "Firewall not implemented")
    def test_inventory_macos_firewall(self):
        """Test inventory macos firewall"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
