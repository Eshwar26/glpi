#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'lib'))

try:
    from GLPI.Agent.Task.Collect.Findfile import Findfile
except ImportError:
    Findfile = None


class TestCollectFindfile(unittest.TestCase):
    
    @unittest.skipIf(Findfile is None, "Findfile not implemented")
    def test_collect_findfile(self):
        """Test collect findfile"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
