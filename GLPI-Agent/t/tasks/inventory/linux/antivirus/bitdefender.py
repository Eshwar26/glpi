#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Linux.Antivirus.Bitdefender import Bitdefender
except ImportError:
    Bitdefender = None


class TestInventoryLinuxAntivirusBitdefender(unittest.TestCase):
    
    @unittest.skipIf(Bitdefender is None, "Bitdefender not implemented")
    def test_inventory_linux_antivirus_bitdefender(self):
        """Test inventory linux antivirus bitdefender"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
