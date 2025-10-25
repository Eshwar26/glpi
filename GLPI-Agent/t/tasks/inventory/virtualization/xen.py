#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Virtualization.Xen import Xen
except ImportError:
    Xen = None


class TestInventoryVirtualizationXen(unittest.TestCase):
    
    @unittest.skipIf(Xen is None, "Xen not implemented")
    def test_inventory_virtualization_xen(self):
        """Test inventory virtualization xen"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
