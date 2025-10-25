#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Generic.Ipmi.Fru_Memories import Fru_Memories
except ImportError:
    Fru_Memories = None


class TestInventoryGenericIpmiFru_Memories(unittest.TestCase):
    
    @unittest.skipIf(Fru_Memories is None, "Fru_Memories not implemented")
    def test_inventory_generic_ipmi_fru_memories(self):
        """Test inventory generic ipmi fru_memories"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
