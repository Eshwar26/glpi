#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Generic.Pci.Modems import Modems
except ImportError:
    Modems = None


class TestInventoryGenericPciModems(unittest.TestCase):
    
    @unittest.skipIf(Modems is None, "Modems not implemented")
    def test_inventory_generic_pci_modems(self):
        """Test inventory generic pci modems"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
