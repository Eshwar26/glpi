#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Generic.Pci.Sounds import Sounds
except ImportError:
    Sounds = None


class TestInventoryGenericPciSounds(unittest.TestCase):
    
    @unittest.skipIf(Sounds is None, "Sounds not implemented")
    def test_inventory_generic_pci_sounds(self):
        """Test inventory generic pci sounds"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
