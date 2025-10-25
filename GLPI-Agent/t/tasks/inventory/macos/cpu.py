#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Macos.Cpu import Cpu
except ImportError:
    Cpu = None


class TestInventoryMacosCpu(unittest.TestCase):
    
    @unittest.skipIf(Cpu is None, "Cpu not implemented")
    def test_inventory_macos_cpu(self):
        """Test inventory macos cpu"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
