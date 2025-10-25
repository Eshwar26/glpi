#!/usr/bin/env python3

import os
import sys
import pytest

sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')

try:
    from GLPI.Agent.XML.Query.SimpleMessage import SimpleMessage
except ImportError:
    SimpleMessage = None


@pytest.mark.skipif(SimpleMessage is None, reason="SimpleMessage not implemented")
class TestXMLQuerySimpleMessage:
    """Tests for XML Query SimpleMessage"""
    
    def test_simple_message(self):
        """Test simple message"""
        pytest.skip("SimpleMessage tests require test data")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
