#!/usr/bin/env python3

import os
import sys
import platform
import pytest

sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')

try:
    from GLPI.Agent.Tools.Solaris import *
except ImportError:
    pass


@pytest.mark.skipif(platform.system() != 'SunOS', reason="Solaris-specific tests")
class TestToolsSolaris:
    """Tests for GLPI Agent Tools Solaris"""
    
    def test_solaris_tools(self):
        """Test Solaris-specific tools"""
        pytest.skip("Solaris tests require Solaris system")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
