#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Windows.Drives import Drives
except ImportError:
    Drives = None


class TestInventoryWindowsDrives(unittest.TestCase):
    
    @unittest.skipIf(Drives is None, "Drives not implemented")
    def test_inventory_windows_drives(self):
        """Test inventory windows drives"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
