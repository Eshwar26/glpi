#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Linux.Antivirus.Defender import Defender
except ImportError:
    Defender = None


class TestInventoryLinuxAntivirusDefender(unittest.TestCase):
    
    @unittest.skipIf(Defender is None, "Defender not implemented")
    def test_inventory_linux_antivirus_defender(self):
        """Test inventory linux antivirus defender"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
