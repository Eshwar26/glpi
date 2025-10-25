#!/usr/bin/env python3

import os
import sys
import pytest

sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')


class TestAppsWakeOnLan:
    """Tests for glpi-wakeonlan application"""
    
    def test_wakeonlan_app(self):
        """Test wakeonlan application"""
        pytest.skip("WakeOnLan tests require network infrastructure")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
