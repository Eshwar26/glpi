#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Windows.Firewall import Firewall
except ImportError:
    Firewall = None


class TestInventoryWindowsFirewall(unittest.TestCase):
    
    @unittest.skipIf(Firewall is None, "Firewall not implemented")
    def test_inventory_windows_firewall(self):
        """Test inventory windows firewall"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
