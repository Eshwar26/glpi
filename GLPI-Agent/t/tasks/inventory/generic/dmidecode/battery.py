#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Generic.Dmidecode.Battery import Battery
except ImportError:
    Battery = None


class TestInventoryGenericDmidecodeBattery(unittest.TestCase):
    
    @unittest.skipIf(Battery is None, "Battery not implemented")
    def test_inventory_generic_dmidecode_battery(self):
        """Test inventory generic dmidecode battery"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
