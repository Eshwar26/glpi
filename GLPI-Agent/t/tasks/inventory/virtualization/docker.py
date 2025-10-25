#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Virtualization.Docker import Docker
except ImportError:
    Docker = None


class TestInventoryVirtualizationDocker(unittest.TestCase):
    
    @unittest.skipIf(Docker is None, "Docker not implemented")
    def test_inventory_virtualization_docker(self):
        """Test inventory virtualization docker"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
