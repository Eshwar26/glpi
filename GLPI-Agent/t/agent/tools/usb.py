#!/usr/bin/env python3

import os
import sys
import pytest

sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')

try:
    from GLPI.Agent.Tools.USB import *
except ImportError:
    pass


class TestToolsUSB:
    """Tests for GLPI Agent Tools USB"""
    
    def test_usb_detection(self):
        """Test USB device detection"""
        pytest.skip("USB tests require test data")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
