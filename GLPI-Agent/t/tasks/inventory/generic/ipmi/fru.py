#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Generic.Ipmi.Fru import Fru
except ImportError:
    Fru = None


class TestInventoryGenericIpmiFru(unittest.TestCase):
    
    @unittest.skipIf(Fru is None, "Fru not implemented")
    def test_inventory_generic_ipmi_fru(self):
        """Test inventory generic ipmi fru"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
