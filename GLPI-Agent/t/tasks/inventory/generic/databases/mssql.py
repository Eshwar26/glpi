#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Generic.Databases.Mssql import Mssql
except ImportError:
    Mssql = None


class TestInventoryGenericDatabasesMssql(unittest.TestCase):
    
    @unittest.skipIf(Mssql is None, "Mssql not implemented")
    def test_inventory_generic_databases_mssql(self):
        """Test inventory generic databases mssql"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
