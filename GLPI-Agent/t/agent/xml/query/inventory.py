#!/usr/bin/env python3

import os
import sys
import pytest

sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')

try:
    from GLPI.Agent.XML.Query.Inventory import Inventory
except ImportError:
    Inventory = None


@pytest.mark.skipif(Inventory is None, reason="Inventory query not implemented")
class TestXMLQueryInventory:
    """Tests for XML Query Inventory"""
    
    def test_inventory_query(self):
        """Test inventory query"""
        pytest.skip("Inventory query tests require test data")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
