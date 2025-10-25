#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Macos.Hostname import Hostname
except ImportError:
    Hostname = None


class TestInventoryMacosHostname(unittest.TestCase):
    
    @unittest.skipIf(Hostname is None, "Hostname not implemented")
    def test_inventory_macos_hostname(self):
        """Test inventory macos hostname"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
