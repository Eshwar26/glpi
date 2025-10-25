#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Linux.Distro import Distro
except ImportError:
    Distro = None


class TestInventoryLinuxDistro(unittest.TestCase):
    
    @unittest.skipIf(Distro is None, "Distro not implemented")
    def test_inventory_linux_distro(self):
        """Test inventory linux distro"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
