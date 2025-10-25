#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Virtualization.Parallels import Parallels
except ImportError:
    Parallels = None


class TestInventoryVirtualizationParallels(unittest.TestCase):
    
    @unittest.skipIf(Parallels is None, "Parallels not implemented")
    def test_inventory_virtualization_parallels(self):
        """Test inventory virtualization parallels"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
