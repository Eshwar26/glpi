#!/usr/bin/env python3

import os
import sys
import platform
import pytest

sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')


@pytest.mark.skipif(platform.system() != 'Linux', reason="Linux-only installer tests")
class TestLinuxInstaller:
    """Tests for Linux installer"""
    
    def test_installer(self):
        """Test Linux installer"""
        pytest.skip("Installer tests require installation infrastructure")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
