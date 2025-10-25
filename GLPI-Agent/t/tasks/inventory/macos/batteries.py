#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Macos.Batteries import Batteries
except ImportError:
    Batteries = None


class TestInventoryMacosBatteries(unittest.TestCase):
    
    @unittest.skipIf(Batteries is None, "Batteries not implemented")
    def test_inventory_macos_batteries(self):
        """Test inventory macos batteries"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
