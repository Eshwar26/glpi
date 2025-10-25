#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Macos.Videos import Videos
except ImportError:
    Videos = None


class TestInventoryMacosVideos(unittest.TestCase):
    
    @unittest.skipIf(Videos is None, "Videos not implemented")
    def test_inventory_macos_videos(self):
        """Test inventory macos videos"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
