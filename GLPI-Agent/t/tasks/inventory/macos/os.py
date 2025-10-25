#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Macos.Os import Os
except ImportError:
    Os = None


class TestInventoryMacosOs(unittest.TestCase):
    
    @unittest.skipIf(Os is None, "Os not implemented")
    def test_inventory_macos_os(self):
        """Test inventory macos os"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
