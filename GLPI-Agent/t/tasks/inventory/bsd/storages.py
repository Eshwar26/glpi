#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Bsd.Storages import Storages
except ImportError:
    Storages = None


class TestInventoryBsdStorages(unittest.TestCase):
    
    @unittest.skipIf(Storages is None, "Storages not implemented")
    def test_inventory_bsd_storages(self):
        """Test inventory bsd storages"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
