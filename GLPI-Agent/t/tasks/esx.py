#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ..', 'lib'))

try:
    from GLPI.Agent.Task.Esx import Esx
except ImportError:
    Esx = None


class TestEsx(unittest.TestCase):
    
    @unittest.skipIf(Esx is None, "Esx not implemented")
    def test_esx(self):
        """Test esx"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
