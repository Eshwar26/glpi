#!/usr/bin/env python3

import os
import sys
import pytest

sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')

try:
    from GLPI.Agent.Tools import Tools
except ImportError:
    Tools = None


class TestAppsESX:
    """Tests for glpi-esx application"""
    
    def test_esx_app(self):
        """Test ESX application"""
        pytest.skip("ESX tests require ESX server connection")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
