#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Virtualization.Jails import Jails
except ImportError:
    Jails = None


class TestInventoryVirtualizationJails(unittest.TestCase):
    
    @unittest.skipIf(Jails is None, "Jails not implemented")
    def test_inventory_virtualization_jails(self):
        """Test inventory virtualization jails"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
