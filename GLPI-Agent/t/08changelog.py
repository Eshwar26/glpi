#!/usr/bin/env python3

import os
import re
import sys
import pytest

# Add lib to path to import GLPI modules
sys.path.insert(0, 'lib')

# Skip test if not running author tests
if not os.environ.get('TEST_AUTHOR'):
    pytest.skip("Author test, set TEST_AUTHOR environment variable to run", allow_module_level=True)


def test_changelog_format():
    """Test that changelog has proper format"""
    try:
        from GLPI.Agent import VERSION
    except ImportError:
        pytest.skip("GLPI.Agent module not available")
        return
    
    try:
        with open('Changes', 'r') as f:
            lines = f.readlines()
            if len(lines) < 3:
                pytest.fail("Changes file has fewer than 3 lines")
            
            # Third line should match: VERSION Day, DD Mon YYYY
            third_line = lines[2].strip()
            pattern = rf"{VERSION} \w{{3}}, \d{{1,2}} \w{{3}} \d{{4}}$"
            
            assert re.search(pattern, third_line), \
                f"Changelog entry doesn't match expected format. Expected pattern: '{pattern}', got: '{third_line}'"
    except FileNotFoundError:
        pytest.fail("Changes file not found")
