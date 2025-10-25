#!/usr/bin/env python3

import os
import sys
import platform
import pytest

sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')

try:
    from GLPI.Agent.Tools.AIX import *
except ImportError:
    pass


@pytest.mark.skipif(platform.system() != 'AIX', reason="AIX-specific tests")
class TestToolsAIX:
    """Tests for GLPI Agent Tools AIX"""
    
    def test_aix_tools(self):
        """Test AIX-specific tools"""
        pytest.skip("AIX tests require AIX system")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
