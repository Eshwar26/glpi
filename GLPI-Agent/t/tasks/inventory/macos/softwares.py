#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Macos.Softwares import Softwares
except ImportError:
    Softwares = None


class TestInventoryMacosSoftwares(unittest.TestCase):
    
    @unittest.skipIf(Softwares is None, "Softwares not implemented")
    def test_inventory_macos_softwares(self):
        """Test inventory macos softwares"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
