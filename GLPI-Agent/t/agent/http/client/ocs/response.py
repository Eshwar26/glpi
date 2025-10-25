#!/usr/bin/env python3

import os
import sys
import pytest

sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')

try:
    from GLPI.Agent.HTTP.Client.OCS import Response
except ImportError:
    Response = None


@pytest.mark.skipif(Response is None, reason="OCS Response not implemented")
class TestOCSResponse:
    """Tests for OCS protocol response handling"""
    
    def test_response_parsing(self):
        """Test response parsing"""
        pytest.skip("Response tests require test data")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
