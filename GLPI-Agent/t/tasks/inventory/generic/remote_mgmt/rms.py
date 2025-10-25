#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Generic.Remote_Mgmt.Rms import Rms
except ImportError:
    Rms = None


class TestInventoryGenericRemote_MgmtRms(unittest.TestCase):
    
    @unittest.skipIf(Rms is None, "Rms not implemented")
    def test_inventory_generic_remote_mgmt_rms(self):
        """Test inventory generic remote_mgmt rms"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
