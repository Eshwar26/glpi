#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Windows.Users import Users
except ImportError:
    Users = None


class TestInventoryWindowsUsers(unittest.TestCase):
    
    @unittest.skipIf(Users is None, "Users not implemented")
    def test_inventory_windows_users(self):
        """Test inventory windows users"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
