#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Generic.Databases.Db2 import Db2
except ImportError:
    Db2 = None


class TestInventoryGenericDatabasesDb2(unittest.TestCase):
    
    @unittest.skipIf(Db2 is None, "Db2 not implemented")
    def test_inventory_generic_databases_db2(self):
        """Test inventory generic databases db2"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
