#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Generic.Remote_Mgmt.Teamviewer import Teamviewer
except ImportError:
    Teamviewer = None


class TestInventoryGenericRemote_MgmtTeamviewer(unittest.TestCase):
    
    @unittest.skipIf(Teamviewer is None, "Teamviewer not implemented")
    def test_inventory_generic_remote_mgmt_teamviewer(self):
        """Test inventory generic remote_mgmt teamviewer"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
