#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Linux.Antivirus.Cortex import Cortex
except ImportError:
    Cortex = None


class TestInventoryLinuxAntivirusCortex(unittest.TestCase):
    
    @unittest.skipIf(Cortex is None, "Cortex not implemented")
    def test_inventory_linux_antivirus_cortex(self):
        """Test inventory linux antivirus cortex"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
