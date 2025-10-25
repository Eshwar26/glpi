#!/usr/bin/env python3

import os
import sys
import pytest

sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')


class TestAppsInventory:
    """Tests for glpi-inventory application"""
    
    def test_inventory_app(self):
        """Test inventory application"""
        pytest.skip("Inventory app tests require implementation")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
