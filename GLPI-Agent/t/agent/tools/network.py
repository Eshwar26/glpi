#!/usr/bin/env python3

import os
import sys
import pytest

sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')

try:
    from GLPI.Agent.Tools.Network import *
except ImportError:
    pass


class TestToolsNetwork:
    """Tests for GLPI Agent Tools Network"""
    
    def test_network_tools(self):
        """Test network tools"""
        pytest.skip("Network tests require test data")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
