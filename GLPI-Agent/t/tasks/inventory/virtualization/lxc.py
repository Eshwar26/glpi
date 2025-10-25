#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Virtualization.Lxc import Lxc
except ImportError:
    Lxc = None


class TestInventoryVirtualizationLxc(unittest.TestCase):
    
    @unittest.skipIf(Lxc is None, "Lxc not implemented")
    def test_inventory_virtualization_lxc(self):
        """Test inventory virtualization lxc"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
