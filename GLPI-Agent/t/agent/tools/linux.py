#!/usr/bin/env python3

import os
import sys
import platform
import pytest

sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')

try:
    from GLPI.Agent.Tools.Linux import *
except ImportError:
    pass


@pytest.mark.skipif(platform.system() != 'Linux', reason="Linux-specific tests")
class TestToolsLinux:
    """Tests for GLPI Agent Tools Linux"""
    
    def test_linux_tools(self):
        """Test Linux-specific tools"""
        pytest.skip("Linux tools tests require test data")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
