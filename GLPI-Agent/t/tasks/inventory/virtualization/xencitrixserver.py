#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Virtualization.Xencitrixserver import Xencitrixserver
except ImportError:
    Xencitrixserver = None


class TestInventoryVirtualizationXencitrixserver(unittest.TestCase):
    
    @unittest.skipIf(Xencitrixserver is None, "Xencitrixserver not implemented")
    def test_inventory_virtualization_xencitrixserver(self):
        """Test inventory virtualization xencitrixserver"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
