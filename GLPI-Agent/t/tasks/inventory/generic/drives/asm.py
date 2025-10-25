#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Generic.Drives.Asm import Asm
except ImportError:
    Asm = None


class TestInventoryGenericDrivesAsm(unittest.TestCase):
    
    @unittest.skipIf(Asm is None, "Asm not implemented")
    def test_inventory_generic_drives_asm(self):
        """Test inventory generic drives asm"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
