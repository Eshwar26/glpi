#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Hpux.Softwares import Softwares
except ImportError:
    Softwares = None


class TestInventoryHpuxSoftwares(unittest.TestCase):
    
    @unittest.skipIf(Softwares is None, "Softwares not implemented")
    def test_inventory_hpux_softwares(self):
        """Test inventory hpux softwares"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
