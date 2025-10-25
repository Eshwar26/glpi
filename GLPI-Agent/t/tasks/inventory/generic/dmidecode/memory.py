#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Generic.Dmidecode.Memory import Memory
except ImportError:
    Memory = None


class TestInventoryGenericDmidecodeMemory(unittest.TestCase):
    
    @unittest.skipIf(Memory is None, "Memory not implemented")
    def test_inventory_generic_dmidecode_memory(self):
        """Test inventory generic dmidecode memory"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
