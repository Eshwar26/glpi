#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Generic.Ipmi.Lan import Lan
except ImportError:
    Lan = None


class TestInventoryGenericIpmiLan(unittest.TestCase):
    
    @unittest.skipIf(Lan is None, "Lan not implemented")
    def test_inventory_generic_ipmi_lan(self):
        """Test inventory generic ipmi lan"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
