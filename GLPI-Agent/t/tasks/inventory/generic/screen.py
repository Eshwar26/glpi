#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Generic.Screen import Screen
except ImportError:
    Screen = None


class TestInventoryGenericScreen(unittest.TestCase):
    
    @unittest.skipIf(Screen is None, "Screen not implemented")
    def test_inventory_generic_screen(self):
        """Test inventory generic screen"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
