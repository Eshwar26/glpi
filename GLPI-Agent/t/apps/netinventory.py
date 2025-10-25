#!/usr/bin/env python3

import os
import sys
import pytest

sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')


class TestAppsNetInventory:
    """Tests for glpi-netinventory application"""
    
    def test_netinventory_app(self):
        """Test netinventory application"""
        pytest.skip("NetInventory tests require network devices")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
