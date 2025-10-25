#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'../'../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Linux.Arm.Board import Board
except ImportError:
    Board = None


class TestInventoryLinuxArmBoard(unittest.TestCase):
    
    @unittest.skipIf(Board is None, "Board not implemented")
    def test_inventory_linux_arm_board(self):
        """Test inventory linux arm board"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
