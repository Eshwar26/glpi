#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Generic.Firewall import Firewall
except ImportError:
    Firewall = None


class TestInventoryGenericFirewall(unittest.TestCase):
    
    @unittest.skipIf(Firewall is None, "Firewall not implemented")
    def test_inventory_generic_firewall(self):
        """Test inventory generic firewall"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
