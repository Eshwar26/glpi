#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Generic.Batteries.Upower import Upower
except ImportError:
    Upower = None


class TestInventoryGenericBatteriesUpower(unittest.TestCase):
    
    @unittest.skipIf(Upower is None, "Upower not implemented")
    def test_inventory_generic_batteries_upower(self):
        """Test inventory generic batteries upower"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
