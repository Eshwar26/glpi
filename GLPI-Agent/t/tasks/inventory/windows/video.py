#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Windows.Video import Video
except ImportError:
    Video = None


class TestInventoryWindowsVideo(unittest.TestCase):
    
    @unittest.skipIf(Video is None, "Video not implemented")
    def test_inventory_windows_video(self):
        """Test inventory windows video"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
