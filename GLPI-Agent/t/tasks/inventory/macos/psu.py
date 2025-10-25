#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Macos.Psu import Psu
except ImportError:
    Psu = None


class TestInventoryMacosPsu(unittest.TestCase):
    
    @unittest.skipIf(Psu is None, "Psu not implemented")
    def test_inventory_macos_psu(self):
        """Test inventory macos psu"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
