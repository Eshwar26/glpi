#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Linux.Storages.Lsilogic import Lsilogic
except ImportError:
    Lsilogic = None


class TestInventoryLinuxStoragesLsilogic(unittest.TestCase):
    
    @unittest.skipIf(Lsilogic is None, "Lsilogic not implemented")
    def test_inventory_linux_storages_lsilogic(self):
        """Test inventory linux storages lsilogic"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
