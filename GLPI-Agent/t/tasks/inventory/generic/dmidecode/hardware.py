#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Generic.Dmidecode.Hardware import Hardware
except ImportError:
    Hardware = None


class TestInventoryGenericDmidecodeHardware(unittest.TestCase):
    
    @unittest.skipIf(Hardware is None, "Hardware not implemented")
    def test_inventory_generic_dmidecode_hardware(self):
        """Test inventory generic dmidecode hardware"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
