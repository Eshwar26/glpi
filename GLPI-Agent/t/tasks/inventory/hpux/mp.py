#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Hpux.Mp import Mp
except ImportError:
    Mp = None


class TestInventoryHpuxMp(unittest.TestCase):
    
    @unittest.skipIf(Mp is None, "Mp not implemented")
    def test_inventory_hpux_mp(self):
        """Test inventory hpux mp"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
