#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Netinventory.Mibsupport.Force10S import Force10S
except ImportError:
    Force10S = None


class TestNetinventoryMibsupportForce10S(unittest.TestCase):
    
    @unittest.skipIf(Force10S is None, "Force10S not implemented")
    def test_netinventory_mibsupport_force10s(self):
        """Test netinventory mibsupport force10s"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
