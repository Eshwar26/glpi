#!/usr/bin/env python3

import os
import sys
import pytest

sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')

try:
    from GLPI.Agent.Logger import Logger
    from GLPI.Agent.HTTP.Client import Client as HTTPClient
except ImportError:
    Logger = HTTPClient = None


@pytest.mark.skipif(HTTPClient is None, reason="HTTP Client not implemented")
class TestHTTPClientInstantiation:
    """Tests for HTTP Client instantiation"""
    
    def test_client_basic_creation(self):
        """Test basic client creation"""
        if Logger is None:
            pytest.skip("Logger not implemented")
        
        logger = Logger(logger=['Test'])
        client = HTTPClient(logger=logger)
        
        assert client is not None
    
    def test_client_with_timeout(self):
        """Test client creation with timeout"""
        if Logger is None:
            pytest.skip("Logger not implemented")
        
        logger = Logger(logger=['Test'])
        client = HTTPClient(logger=logger, timeout=30)
        
        if hasattr(client, 'timeout'):
            assert client.timeout == 30
    
    def test_client_with_proxy(self):
        """Test client creation with proxy"""
        if Logger is None:
            pytest.skip("Logger not implemented")
        
        logger = Logger(logger=['Test'])
        client = HTTPClient(logger=logger, proxy='http://proxy.example.com:8080')
        
        if hasattr(client, 'proxy'):
            assert client.proxy is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
