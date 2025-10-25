#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Generic.Batteries.Acpiconf import Acpiconf
except ImportError:
    Acpiconf = None


class TestInventoryGenericBatteriesAcpiconf(unittest.TestCase):
    
    @unittest.skipIf(Acpiconf is None, "Acpiconf not implemented")
    def test_inventory_generic_batteries_acpiconf(self):
        """Test inventory generic batteries acpiconf"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
