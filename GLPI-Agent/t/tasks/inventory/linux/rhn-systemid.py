#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Linux.Rhn-Systemid import Rhn-Systemid
except ImportError:
    Rhn-Systemid = None


class TestInventoryLinuxRhn-Systemid(unittest.TestCase):
    
    @unittest.skipIf(Rhn-Systemid is None, "Rhn-Systemid not implemented")
    def test_inventory_linux_rhn-systemid(self):
        """Test inventory linux rhn-systemid"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
