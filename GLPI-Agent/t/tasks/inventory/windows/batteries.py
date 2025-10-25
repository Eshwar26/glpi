#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Windows.Batteries import Batteries
except ImportError:
    Batteries = None


class TestInventoryWindowsBatteries(unittest.TestCase):
    
    @unittest.skipIf(Batteries is None, "Batteries not implemented")
    def test_inventory_windows_batteries(self):
        """Test inventory windows batteries"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
