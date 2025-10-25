#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Windows.Printers import Printers
except ImportError:
    Printers = None


class TestInventoryWindowsPrinters(unittest.TestCase):
    
    @unittest.skipIf(Printers is None, "Printers not implemented")
    def test_inventory_windows_printers(self):
        """Test inventory windows printers"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
