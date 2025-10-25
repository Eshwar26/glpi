#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Generic.Dmidecode.Slots import Slots
except ImportError:
    Slots = None


class TestInventoryGenericDmidecodeSlots(unittest.TestCase):
    
    @unittest.skipIf(Slots is None, "Slots not implemented")
    def test_inventory_generic_dmidecode_slots(self):
        """Test inventory generic dmidecode slots"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
