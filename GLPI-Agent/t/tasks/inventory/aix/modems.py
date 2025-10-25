#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Aix.Modems import Modems
except ImportError:
    Modems = None


class TestInventoryAixModems(unittest.TestCase):
    
    @unittest.skipIf(Modems is None, "Modems not implemented")
    def test_inventory_aix_modems(self):
        """Test inventory aix modems"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
