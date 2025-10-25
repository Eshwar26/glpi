#!/usr/bin/env python3

import os
import sys
import pytest

sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')

try:
    from GLPI.Agent.Tools.Storages.HP import *
except ImportError:
    pass


class TestToolsStoragesHP:
    """Tests for GLPI Agent Tools Storages HP"""
    
    def test_hp_storage_detection(self):
        """Test HP storage detection"""
        pytest.skip("HP storage tests require HP hardware")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
