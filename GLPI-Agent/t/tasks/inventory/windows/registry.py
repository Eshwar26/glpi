#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Windows.Registry import Registry
except ImportError:
    Registry = None


class TestInventoryWindowsRegistry(unittest.TestCase):
    
    @unittest.skipIf(Registry is None, "Registry not implemented")
    def test_inventory_windows_registry(self):
        """Test inventory windows registry"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
