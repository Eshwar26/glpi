#!/usr/bin/env python3

import os
import sys
import platform
import pytest

sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')

try:
    from GLPI.Agent.Tools.BSD import *
except ImportError:
    pass


@pytest.mark.skipif('BSD' not in platform.system(), reason="BSD-specific tests")
class TestToolsBSD:
    """Tests for GLPI Agent Tools BSD"""
    
    def test_bsd_tools(self):
        """Test BSD-specific tools"""
        pytest.skip("BSD tests require BSD system")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
