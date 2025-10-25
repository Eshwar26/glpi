#!/usr/bin/env python3

import os
import sys
import platform
import pytest

sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')

try:
    from GLPI.Agent.Tools.Win32 import *
except ImportError:
    pass


@pytest.mark.skipif(platform.system() != 'Windows', reason="Windows-specific tests")
class TestToolsWin32:
    """Tests for GLPI Agent Tools Win32"""
    
    def test_win32_tools(self):
        """Test Windows-specific tools"""
        pytest.skip("Win32 tools tests require test data")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
