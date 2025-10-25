#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Solaris.Os import Os
except ImportError:
    Os = None


class TestInventorySolarisOs(unittest.TestCase):
    
    @unittest.skipIf(Os is None, "Os not implemented")
    def test_inventory_solaris_os(self):
        """Test inventory solaris os"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
