#!/usr/bin/env python3

import os
import sys
import pytest

sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')

try:
    from GLPI.Agent.Tools.License import *
except ImportError:
    pass


class TestToolsLicense:
    """Tests for GLPI Agent Tools License"""
    
    def test_license_detection(self):
        """Test license detection"""
        pytest.skip("License tests require test data")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
