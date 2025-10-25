#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Hpux.Drives import Drives
except ImportError:
    Drives = None


class TestInventoryHpuxDrives(unittest.TestCase):
    
    @unittest.skipIf(Drives is None, "Drives not implemented")
    def test_inventory_hpux_drives(self):
        """Test inventory hpux drives"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
