#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Hpux.Cpu import Cpu
except ImportError:
    Cpu = None


class TestInventoryHpuxCpu(unittest.TestCase):
    
    @unittest.skipIf(Cpu is None, "Cpu not implemented")
    def test_inventory_hpux_cpu(self):
        """Test inventory hpux cpu"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
