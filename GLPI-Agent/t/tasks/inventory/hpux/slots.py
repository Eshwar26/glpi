#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Hpux.Slots import Slots
except ImportError:
    Slots = None


class TestInventoryHpuxSlots(unittest.TestCase):
    
    @unittest.skipIf(Slots is None, "Slots not implemented")
    def test_inventory_hpux_slots(self):
        """Test inventory hpux slots"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
