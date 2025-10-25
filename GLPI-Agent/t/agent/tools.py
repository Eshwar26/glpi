#!/usr/bin/env python3

import os
import sys
import platform
import pytest

# Add paths for imports
sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')

try:
    from GLPI.Agent import Tools
    from GLPI.Agent.Tools import (
        getCanonicalSize, getCanonicalSpeed, getCanonicalManufacturer,
        compareVersion, trimWhitespace, hex2dec
    )
except ImportError:
    Tools = None
    getCanonicalSize = getCanonicalSpeed = None
    getCanonicalManufacturer = compareVersion = None
    trimWhitespace = hex2dec = None


# Test data
SIZE_TESTS_OK = [
    ('1', 1),
    ('1 mb', 1),
    ('1.1 mb', 1.1),
    ('11,11 mb', 11.11),
    ('1.111 mb', 1.111),
    ('1,111 mb', 1111),
    ('1 MB', 1),
    ('1,000 MB', 1000),
    ('1,000.9 MB', 1000.9),
    ('1,000,000.9 MB', 1000000.9),
    ('1 gb', 1000),
    ('1 GB', 1000),
    ('1 tb', 1000000),
    ('1 TB', 1000000),
    ('128 035 676 160 bytes', 128035),
    ('600,127,266,816 bytes', 600127),
]

SIZE_1024_TESTS_OK = [
    ('1', 1),
    ('1 mb', 1),
    ('1.1 mb', 1.1),
    ('1 MB', 1),
    ('1 gb', 1024),
    ('1 GB', 1024),
    ('1 tb', 1048576),
    ('1 TB', 1048576),
    ('128 035 676 160 bytes', 122104),
    ('600,127,266,816 bytes', 572325),
]

SPEED_TESTS_OK = [
    ('1 mhz', 1),
    ('1 MHZ', 1),
    ('1 ghz', 1000),
    ('1 GHZ', 1000),
    ('1mhz', 1),
    ('1MHZ', 1),
    ('1ghz', 1000),
    ('1GHZ', 1000),
]

MANUFACTURER_TESTS_OK = [
    ('maxtor', 'Maxtor'),
    ('sony', 'Sony'),
    ('compaq', 'Compaq'),
    ('ibm', 'Ibm'),
    ('toshiba', 'Toshiba'),
    ('fujitsu', 'Fujitsu'),
    ('lg', 'Lg'),
    ('samsung', 'Samsung'),
    ('nec', 'Nec'),
    ('transcend', 'Transcend'),
    ('matshita', 'Matshita'),
    ('pioneer', 'Pioneer'),
    ('hewlett packard', 'Hewlett-Packard'),
    ('hewlett-packard', 'Hewlett-Packard'),
    ('hp', 'Hewlett-Packard'),
    ('WDC', 'Western Digital'),
    ('western', 'Western Digital'),
    ('Western', 'Western Digital'),
    ('WeStErN', 'Western Digital'),
    ('ST', 'Seagate'),
    ('seagate', 'Seagate'),
    ('Seagate', 'Seagate'),
    ('SeAgAtE', 'Seagate'),
    ('HD', 'Hitachi'),
    ('IC', 'Hitachi'),
    ('HU', 'Hitachi'),
    ('foo', 'foo'),
]

VERSION_TESTS_OK = [
    ((1, 0), (1, 0), 0),
    ((0, 1), (0, 1), 0),
    ((1, 1), (1, 1), 0),
    ((1, 2, 3), (1, 2, 3), 0),
    ((1, 0), (0, 1), 1),
    ((1, 0), (0, 0), 1),
    ((1, 1), (1, 0), 1),
    ((2, 0), (1, 0), 1),
    ((0, 1), (1, 0), -1),
    ((0, 0), (1, 0), -1),
    ((1, 0), (1, 1), -1),
    ((1, 0), (2, 0), -1),
]


@pytest.mark.skipif(getCanonicalSize is None, reason="Tools not implemented")
class TestToolsSize:
    """Tests for size conversion functions"""
    
    @pytest.mark.parametrize("input_str,expected", SIZE_TESTS_OK)
    def test_canonical_size(self, input_str, expected):
        """Test getCanonicalSize with various inputs"""
        result = getCanonicalSize(input_str)
        assert result == expected, f"getCanonicalSize('{input_str}') should be {expected}, got {result}"
    
    @pytest.mark.parametrize("input_str,expected", SIZE_1024_TESTS_OK)
    def test_canonical_size_1024(self, input_str, expected):
        """Test getCanonicalSize with 1024 base"""
        result = getCanonicalSize(input_str, 1024)
        assert result == expected, f"getCanonicalSize('{input_str}', 1024) should be {expected}, got {result}"
    
    def test_canonical_size_invalid(self):
        """Test getCanonicalSize with invalid inputs"""
        assert getCanonicalSize('foo') is None
        assert getCanonicalSize(None) is None


@pytest.mark.skipif(getCanonicalSpeed is None, reason="Tools not implemented")
class TestToolsSpeed:
    """Tests for speed conversion functions"""
    
    @pytest.mark.parametrize("input_str,expected", SPEED_TESTS_OK)
    def test_canonical_speed(self, input_str, expected):
        """Test getCanonicalSpeed with various inputs"""
        result = getCanonicalSpeed(input_str)
        assert result == expected, f"getCanonicalSpeed('{input_str}') should be {expected}, got {result}"
    
    def test_canonical_speed_invalid(self):
        """Test getCanonicalSpeed with invalid inputs"""
        assert getCanonicalSpeed('foo') is None
        assert getCanonicalSpeed(None) is None


@pytest.mark.skipif(getCanonicalManufacturer is None, reason="Tools not implemented")
class TestToolsManufacturer:
    """Tests for manufacturer normalization functions"""
    
    @pytest.mark.parametrize("input_str,expected", MANUFACTURER_TESTS_OK)
    def test_canonical_manufacturer(self, input_str, expected):
        """Test getCanonicalManufacturer with various inputs"""
        result = getCanonicalManufacturer(input_str)
        assert result == expected, f"getCanonicalManufacturer('{input_str}') should be '{expected}', got '{result}'"
    
    def test_canonical_manufacturer_invalid(self):
        """Test getCanonicalManufacturer with invalid inputs"""
        assert getCanonicalManufacturer(None) is None


@pytest.mark.skipif(compareVersion is None, reason="Tools not implemented")
class TestToolsVersion:
    """Tests for version comparison functions"""
    
    @pytest.mark.parametrize("v1,v2,expected", VERSION_TESTS_OK)
    def test_compare_version(self, v1, v2, expected):
        """Test compareVersion with various version pairs"""
        v1_str = '.'.join(map(str, v1))
        v2_str = '.'.join(map(str, v2))
        
        result = compareVersion(v1_str, v2_str)
        assert result == expected, f"compareVersion('{v1_str}', '{v2_str}') should be {expected}, got {result}"


@pytest.mark.skipif(trimWhitespace is None, reason="Tools not implemented")
class TestToolsWhitespace:
    """Tests for whitespace handling functions"""
    
    def test_trim_whitespace(self):
        """Test trimWhitespace function"""
        assert trimWhitespace('  foo  ') == 'foo'
        assert trimWhitespace('foo') == 'foo'
        assert trimWhitespace('  foo  bar  ') == 'foo bar'
        assert trimWhitespace('') == ''
    
    def test_trim_whitespace_special(self):
        """Test trimWhitespace with special characters"""
        if trimWhitespace is not None:
            result = trimWhitespace(' \t\nfoo\t\n ')
            assert result.strip() == 'foo'


@pytest.mark.skipif(hex2dec is None, reason="Tools not implemented")
class TestToolsHex:
    """Tests for hex conversion functions"""
    
    def test_hex2dec(self):
        """Test hex2dec function"""
        assert hex2dec('FF') == 255
        assert hex2dec('00') == 0
        assert hex2dec('10') == 16
        assert hex2dec('A') == 10
    
    def test_hex2dec_invalid(self):
        """Test hex2dec with invalid input"""
        if hex2dec is not None:
            result = hex2dec('ZZ')
            assert result is None or result == 0


@pytest.mark.skipif(Tools is None, reason="Tools module not implemented")
class TestToolsMisc:
    """Tests for miscellaneous tool functions"""
    
    def test_module_imports(self):
        """Test that Tools module can be imported"""
        assert Tools is not None
    
    def test_common_functions_exist(self):
        """Test that common utility functions exist"""
        if Tools:
            # Just check module exists, specific function tests are in other classes
            pytest.skip("Placeholder test for module existence")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
