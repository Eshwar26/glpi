#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Generic.Pci.Videos.Nvidia import Nvidia
except ImportError:
    Nvidia = None


class TestInventoryGenericPciVideosNvidia(unittest.TestCase):
    
    @unittest.skipIf(Nvidia is None, "Nvidia not implemented")
    def test_inventory_generic_pci_videos_nvidia(self):
        """Test inventory generic pci videos nvidia"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
