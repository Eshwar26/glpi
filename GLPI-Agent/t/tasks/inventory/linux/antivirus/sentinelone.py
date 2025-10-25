#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Linux.Antivirus.Sentinelone import Sentinelone
except ImportError:
    Sentinelone = None


class TestInventoryLinuxAntivirusSentinelone(unittest.TestCase):
    
    @unittest.skipIf(Sentinelone is None, "Sentinelone not implemented")
    def test_inventory_linux_antivirus_sentinelone(self):
        """Test inventory linux antivirus sentinelone"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
