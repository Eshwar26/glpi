#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Virtualization.Libvirt import Libvirt
except ImportError:
    Libvirt = None


class TestInventoryVirtualizationLibvirt(unittest.TestCase):
    
    @unittest.skipIf(Libvirt is None, "Libvirt not implemented")
    def test_inventory_virtualization_libvirt(self):
        """Test inventory virtualization libvirt"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
