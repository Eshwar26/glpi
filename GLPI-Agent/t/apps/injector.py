#!/usr/bin/env python3

import os
import sys
import pytest

sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')


class TestAppsInjector:
    """Tests for glpi-injector application"""
    
    def test_injector_app(self):
        """Test injector application"""
        pytest.skip("Injector tests require test data")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
