#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Macos.Uptime import Uptime
except ImportError:
    Uptime = None


class TestInventoryMacosUptime(unittest.TestCase):
    
    @unittest.skipIf(Uptime is None, "Uptime not implemented")
    def test_inventory_macos_uptime(self):
        """Test inventory macos uptime"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
