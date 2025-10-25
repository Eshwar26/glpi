#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Aix.Bios import Bios
except ImportError:
    Bios = None


class TestInventoryAixBios(unittest.TestCase):
    
    @unittest.skipIf(Bios is None, "Bios not implemented")
    def test_inventory_aix_bios(self):
        """Test inventory aix bios"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
