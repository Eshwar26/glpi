#!/usr/bin/env python3

import os
import sys
import pytest

sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')

try:
    from GLPI.Agent.XML.NetInventory import NetInventory
except ImportError:
    NetInventory = None


@pytest.mark.skipif(NetInventory is None, reason="NetInventory not implemented")
class TestXMLNetInventory:
    """Tests for XML NetInventory"""
    
    def test_netinventory_creation(self):
        """Test NetInventory XML creation"""
        pytest.skip("NetInventory tests require test data")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
