#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Virtualization.Hyperv import Hyperv
except ImportError:
    Hyperv = None


class TestInventoryVirtualizationHyperv(unittest.TestCase):
    
    @unittest.skipIf(Hyperv is None, "Hyperv not implemented")
    def test_inventory_virtualization_hyperv(self):
        """Test inventory virtualization hyperv"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
