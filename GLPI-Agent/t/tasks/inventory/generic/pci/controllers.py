#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Generic.Pci.Controllers import Controllers
except ImportError:
    Controllers = None


class TestInventoryGenericPciControllers(unittest.TestCase):
    
    @unittest.skipIf(Controllers is None, "Controllers not implemented")
    def test_inventory_generic_pci_controllers(self):
        """Test inventory generic pci controllers"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
