#!/usr/bin/env python3

import os
import sys
import pytest

sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')

try:
    from GLPI.Agent.HTTP.Client.OCS import Compression
except ImportError:
    Compression = None


@pytest.mark.skipif(Compression is None, reason="OCS Compression not implemented")
class TestOCSCompression:
    """Tests for OCS protocol compression"""
    
    def test_compression(self):
        """Test data compression"""
        pytest.skip("Compression tests require test data")
    
    def test_decompression(self):
        """Test data decompression"""
        pytest.skip("Decompression tests require test data")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
