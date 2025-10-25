#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Generic.Databases.Mongodb import Mongodb
except ImportError:
    Mongodb = None


class TestInventoryGenericDatabasesMongodb(unittest.TestCase):
    
    @unittest.skipIf(Mongodb is None, "Mongodb not implemented")
    def test_inventory_generic_databases_mongodb(self):
        """Test inventory generic databases mongodb"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
