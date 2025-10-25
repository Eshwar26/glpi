#!/usr/bin/env python3

import os
import sys
import pytest

sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')

try:
    from GLPI.Agent.SNMP.Live import Live
except ImportError:
    Live = None


@pytest.mark.skipif(Live is None, reason="SNMP Live not implemented")
class TestSNMPLive:
    """Tests for GLPI Agent SNMP Live"""
    
    def test_snmp_creation(self):
        """Test SNMP session creation"""
        pytest.skip("SNMP tests require SNMP agent/daemon")
    
    def test_snmp_get(self):
        """Test SNMP GET operation"""
        pytest.skip("SNMP tests require SNMP agent")
    
    def test_snmp_walk(self):
        """Test SNMP WALK operation"""
        pytest.skip("SNMP tests require SNMP agent")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
