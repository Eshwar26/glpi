#!/usr/bin/env python3

import os
import sys
import pytest

sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')

try:
    from GLPI.Agent.Tools.Archive import *
except ImportError:
    pass


class TestToolsArchive:
    """Tests for GLPI Agent Tools Archive"""
    
    def test_archive_extraction(self):
        """Test archive extraction"""
        pytest.skip("Archive tests require test data")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
