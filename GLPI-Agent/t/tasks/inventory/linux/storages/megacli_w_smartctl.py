#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Linux.Storages.Megacli_W_Smartctl import Megacli_W_Smartctl
except ImportError:
    Megacli_W_Smartctl = None


class TestInventoryLinuxStoragesMegacli_W_Smartctl(unittest.TestCase):
    
    @unittest.skipIf(Megacli_W_Smartctl is None, "Megacli_W_Smartctl not implemented")
    def test_inventory_linux_storages_megacli_w_smartctl(self):
        """Test inventory linux storages megacli_w_smartctl"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
