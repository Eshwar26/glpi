#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'lib'))

try:
    from GLPI.Agent.Task.Deploy.Checkprocessor import Checkprocessor
except ImportError:
    Checkprocessor = None


class TestDeployCheckprocessor(unittest.TestCase):
    
    @unittest.skipIf(Checkprocessor is None, "Checkprocessor not implemented")
    def test_deploy_checkprocessor(self):
        """Test deploy checkprocessor"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
