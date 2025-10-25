#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Macos.Antivirus import Antivirus
except ImportError:
    Antivirus = None


class TestInventoryMacosAntivirus(unittest.TestCase):
    
    @unittest.skipIf(Antivirus is None, "Antivirus not implemented")
    def test_inventory_macos_antivirus(self):
        """Test inventory macos antivirus"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
