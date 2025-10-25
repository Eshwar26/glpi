#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Linux.Storages.Adaptec import Adaptec
except ImportError:
    Adaptec = None


class TestInventoryLinuxStoragesAdaptec(unittest.TestCase):
    
    @unittest.skipIf(Adaptec is None, "Adaptec not implemented")
    def test_inventory_linux_storages_adaptec(self):
        """Test inventory linux storages adaptec"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
