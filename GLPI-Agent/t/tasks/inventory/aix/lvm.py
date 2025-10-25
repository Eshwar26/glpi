#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Aix.Lvm import Lvm
except ImportError:
    Lvm = None


class TestInventoryAixLvm(unittest.TestCase):
    
    @unittest.skipIf(Lvm is None, "Lvm not implemented")
    def test_inventory_aix_lvm(self):
        """Test inventory aix lvm"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
