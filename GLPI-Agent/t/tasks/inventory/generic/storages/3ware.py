#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Generic.Storages.3Ware import 3Ware
except ImportError:
    3Ware = None


class TestInventoryGenericStorages3Ware(unittest.TestCase):
    
    @unittest.skipIf(3Ware is None, "3Ware not implemented")
    def test_inventory_generic_storages_3ware(self):
        """Test inventory generic storages 3ware"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
