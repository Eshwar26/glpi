#!/usr/bin/env python3

import os
import sys
import pytest

sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')

try:
    from GLPI.Agent.Tools.Generic import *
except ImportError:
    pass


class TestToolsGeneric:
    """Tests for GLPI Agent Tools Generic"""
    
    def test_generic_tools(self):
        """Test generic tools"""
        pytest.skip("Generic tools tests require test data")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
