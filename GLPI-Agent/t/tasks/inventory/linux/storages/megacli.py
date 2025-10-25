#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Linux.Storages.Megacli import Megacli
except ImportError:
    Megacli = None


class TestInventoryLinuxStoragesMegacli(unittest.TestCase):
    
    @unittest.skipIf(Megacli is None, "Megacli not implemented")
    def test_inventory_linux_storages_megacli(self):
        """Test inventory linux storages megacli"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
