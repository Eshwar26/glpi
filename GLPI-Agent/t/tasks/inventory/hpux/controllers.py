#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Hpux.Controllers import Controllers
except ImportError:
    Controllers = None


class TestInventoryHpuxControllers(unittest.TestCase):
    
    @unittest.skipIf(Controllers is None, "Controllers not implemented")
    def test_inventory_hpux_controllers(self):
        """Test inventory hpux controllers"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
