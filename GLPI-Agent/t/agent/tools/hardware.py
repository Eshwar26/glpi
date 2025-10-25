#!/usr/bin/env python3

import os
import sys
import pytest

sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')

try:
    from GLPI.Agent.Tools.Hardware import *
except ImportError:
    pass


class TestToolsHardware:
    """Tests for GLPI Agent Tools Hardware"""
    
    def test_hardware_detection(self):
        """Test hardware detection"""
        pytest.skip("Hardware tests require specific hardware")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
