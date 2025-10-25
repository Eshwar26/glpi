#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Linux.Storages.Megaraid import Megaraid
except ImportError:
    Megaraid = None


class TestInventoryLinuxStoragesMegaraid(unittest.TestCase):
    
    @unittest.skipIf(Megaraid is None, "Megaraid not implemented")
    def test_inventory_linux_storages_megaraid(self):
        """Test inventory linux storages megaraid"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
