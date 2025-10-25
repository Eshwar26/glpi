#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Virtualization.Virtualbox import Virtualbox
except ImportError:
    Virtualbox = None


class TestInventoryVirtualizationVirtualbox(unittest.TestCase):
    
    @unittest.skipIf(Virtualbox is None, "Virtualbox not implemented")
    def test_inventory_virtualization_virtualbox(self):
        """Test inventory virtualization virtualbox"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
