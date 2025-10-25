#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Generic.Ipmi.Fru_Controllers import Fru_Controllers
except ImportError:
    Fru_Controllers = None


class TestInventoryGenericIpmiFru_Controllers(unittest.TestCase):
    
    @unittest.skipIf(Fru_Controllers is None, "Fru_Controllers not implemented")
    def test_inventory_generic_ipmi_fru_controllers(self):
        """Test inventory generic ipmi fru_controllers"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
