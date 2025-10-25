#!/usr/bin/env python3

import os
import sys
import platform
import pytest

sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')

try:
    from GLPI.Agent.Tools.Unix import *
except ImportError:
    pass


@pytest.mark.skipif(platform.system() == 'Windows', reason="Unix-specific tests")
class TestToolsUnix:
    """Tests for GLPI Agent Tools Unix"""
    
    def test_unix_tools(self):
        """Test Unix tools"""
        pytest.skip("Unix tools tests require test data")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
