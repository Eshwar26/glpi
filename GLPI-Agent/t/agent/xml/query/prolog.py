#!/usr/bin/env python3

import os
import sys
import pytest

sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')

try:
    from GLPI.Agent.XML.Query.Prolog import Prolog
except ImportError:
    Prolog = None


@pytest.mark.skipif(Prolog is None, reason="Prolog query not implemented")
class TestXMLQueryProlog:
    """Tests for XML Query Prolog"""
    
    def test_prolog_query(self):
        """Test prolog query"""
        pytest.skip("Prolog query tests require test data")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
