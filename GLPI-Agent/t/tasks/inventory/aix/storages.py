#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Aix.Storages import Storages
except ImportError:
    Storages = None


class TestInventoryAixStorages(unittest.TestCase):
    
    @unittest.skipIf(Storages is None, "Storages not implemented")
    def test_inventory_aix_storages(self):
        """Test inventory aix storages"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
