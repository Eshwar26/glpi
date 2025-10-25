#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Generic.Pci.Videos import Videos
except ImportError:
    Videos = None


class TestInventoryGenericPciVideos(unittest.TestCase):
    
    @unittest.skipIf(Videos is None, "Videos not implemented")
    def test_inventory_generic_pci_videos(self):
        """Test inventory generic pci videos"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
