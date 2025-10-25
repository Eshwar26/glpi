#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Macos.Memory import Memory
except ImportError:
    Memory = None


class TestInventoryMacosMemory(unittest.TestCase):
    
    @unittest.skipIf(Memory is None, "Memory not implemented")
    def test_inventory_macos_memory(self):
        """Test inventory macos memory"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
