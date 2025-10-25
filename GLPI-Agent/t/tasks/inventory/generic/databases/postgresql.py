#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Generic.Databases.Postgresql import Postgresql
except ImportError:
    Postgresql = None


class TestInventoryGenericDatabasesPostgresql(unittest.TestCase):
    
    @unittest.skipIf(Postgresql is None, "Postgresql not implemented")
    def test_inventory_generic_databases_postgresql(self):
        """Test inventory generic databases postgresql"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
