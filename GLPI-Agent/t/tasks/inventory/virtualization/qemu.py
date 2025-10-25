#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Virtualization.Qemu import Qemu
except ImportError:
    Qemu = None


class TestInventoryVirtualizationQemu(unittest.TestCase):
    
    @unittest.skipIf(Qemu is None, "Qemu not implemented")
    def test_inventory_virtualization_qemu(self):
        """Test inventory virtualization qemu"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
