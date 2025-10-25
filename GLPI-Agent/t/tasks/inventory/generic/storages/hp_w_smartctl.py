#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Generic.Storages.Hp_W_Smartctl import Hp_W_Smartctl
except ImportError:
    Hp_W_Smartctl = None


class TestInventoryGenericStoragesHp_W_Smartctl(unittest.TestCase):
    
    @unittest.skipIf(Hp_W_Smartctl is None, "Hp_W_Smartctl not implemented")
    def test_inventory_generic_storages_hp_w_smartctl(self):
        """Test inventory generic storages hp_w_smartctl"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
