#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Generic.Dmidecode.Ports import Ports
except ImportError:
    Ports = None


class TestInventoryGenericDmidecodePorts(unittest.TestCase):
    
    @unittest.skipIf(Ports is None, "Ports not implemented")
    def test_inventory_generic_dmidecode_ports(self):
        """Test inventory generic dmidecode ports"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
