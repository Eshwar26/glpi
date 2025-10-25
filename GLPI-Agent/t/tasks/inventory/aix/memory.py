#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Aix.Memory import Memory
except ImportError:
    Memory = None


class TestInventoryAixMemory(unittest.TestCase):
    
    @unittest.skipIf(Memory is None, "Memory not implemented")
    def test_inventory_aix_memory(self):
        """Test inventory aix memory"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
