#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'lib'))

try:
    from GLPI.Agent.Task.Deploy.Actionprocessor import Actionprocessor
except ImportError:
    Actionprocessor = None


class TestDeployActionprocessor(unittest.TestCase):
    
    @unittest.skipIf(Actionprocessor is None, "Actionprocessor not implemented")
    def test_deploy_actionprocessor(self):
        """Test deploy actionprocessor"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
