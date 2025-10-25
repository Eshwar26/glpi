#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Windows.License import License
except ImportError:
    License = None


class TestInventoryWindowsLicense(unittest.TestCase):
    
    @unittest.skipIf(License is None, "License not implemented")
    def test_inventory_windows_license(self):
        """Test inventory windows license"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
