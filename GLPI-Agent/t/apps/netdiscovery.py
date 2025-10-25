#!/usr/bin/env python3

import os
import sys
import pytest

sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')


class TestAppsNetDiscovery:
    """Tests for glpi-netdiscovery application"""
    
    def test_netdiscovery_app(self):
        """Test netdiscovery application"""
        pytest.skip("NetDiscovery tests require network infrastructure")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
