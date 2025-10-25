#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Linux.Networks.Dockermacvlan import Dockermacvlan
except ImportError:
    Dockermacvlan = None


class TestInventoryLinuxNetworksDockermacvlan(unittest.TestCase):
    
    @unittest.skipIf(Dockermacvlan is None, "Dockermacvlan not implemented")
    def test_inventory_linux_networks_dockermacvlan(self):
        """Test inventory linux networks dockermacvlan"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
