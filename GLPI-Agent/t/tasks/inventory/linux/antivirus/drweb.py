#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Linux.Antivirus.Drweb import Drweb
except ImportError:
    Drweb = None


class TestInventoryLinuxAntivirusDrweb(unittest.TestCase):
    
    @unittest.skipIf(Drweb is None, "Drweb not implemented")
    def test_inventory_linux_antivirus_drweb(self):
        """Test inventory linux antivirus drweb"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
