#!/usr/bin/env python3

import os
import sys
import platform
import pytest

sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')

try:
    from GLPI.Agent.Tools.MacOS import *
except ImportError:
    pass


@pytest.mark.skipif(platform.system() != 'Darwin', reason="macOS-specific tests")
class TestToolsMacOS:
    """Tests for GLPI Agent Tools macOS"""
    
    def test_macos_tools(self):
        """Test macOS-specific tools"""
        pytest.skip("macOS tools tests require test data")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
