#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Linux.Antivirus.Kesl import Kesl
except ImportError:
    Kesl = None


class TestInventoryLinuxAntivirusKesl(unittest.TestCase):
    
    @unittest.skipIf(Kesl is None, "Kesl not implemented")
    def test_inventory_linux_antivirus_kesl(self):
        """Test inventory linux antivirus kesl"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
