#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Generic.Databases.Mysql import Mysql
except ImportError:
    Mysql = None


class TestInventoryGenericDatabasesMysql(unittest.TestCase):
    
    @unittest.skipIf(Mysql is None, "Mysql not implemented")
    def test_inventory_generic_databases_mysql(self):
        """Test inventory generic databases mysql"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
