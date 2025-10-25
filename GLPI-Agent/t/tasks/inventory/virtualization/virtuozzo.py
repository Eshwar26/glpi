#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Virtualization.Virtuozzo import Virtuozzo
except ImportError:
    Virtuozzo = None


class TestInventoryVirtualizationVirtuozzo(unittest.TestCase):
    
    @unittest.skipIf(Virtuozzo is None, "Virtuozzo not implemented")
    def test_inventory_virtualization_virtuozzo(self):
        """Test inventory virtualization virtuozzo"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
