#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Generic.Databases.Oracle import Oracle
except ImportError:
    Oracle = None


class TestInventoryGenericDatabasesOracle(unittest.TestCase):
    
    @unittest.skipIf(Oracle is None, "Oracle not implemented")
    def test_inventory_generic_databases_oracle(self):
        """Test inventory generic databases oracle"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
