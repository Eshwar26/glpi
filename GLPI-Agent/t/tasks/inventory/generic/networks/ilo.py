#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Generic.Networks.Ilo import Ilo
except ImportError:
    Ilo = None


class TestInventoryGenericNetworksIlo(unittest.TestCase):
    
    @unittest.skipIf(Ilo is None, "Ilo not implemented")
    def test_inventory_generic_networks_ilo(self):
        """Test inventory generic networks ilo"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
