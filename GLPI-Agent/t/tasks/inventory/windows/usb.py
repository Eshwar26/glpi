#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Windows.Usb import Usb
except ImportError:
    Usb = None


class TestInventoryWindowsUsb(unittest.TestCase):
    
    @unittest.skipIf(Usb is None, "Usb not implemented")
    def test_inventory_windows_usb(self):
        """Test inventory windows usb"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
