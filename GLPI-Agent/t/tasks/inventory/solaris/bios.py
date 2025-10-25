#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Solaris.Bios import Bios
except ImportError:
    Bios = None


class TestInventorySolarisBios(unittest.TestCase):
    
    @unittest.skipIf(Bios is None, "Bios not implemented")
    def test_inventory_solaris_bios(self):
        """Test inventory solaris bios"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
