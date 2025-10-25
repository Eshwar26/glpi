#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Solaris.Drives import Drives
except ImportError:
    Drives = None


class TestInventorySolarisDrives(unittest.TestCase):
    
    @unittest.skipIf(Drives is None, "Drives not implemented")
    def test_inventory_solaris_drives(self):
        """Test inventory solaris drives"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
