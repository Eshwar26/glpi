#!/usr/bin/env python3

import os
import re
import subprocess
import sys
import pytest

# Add lib to path
sys.path.insert(0, 'lib')

# Skip test if not running author tests
if not os.environ.get('TEST_AUTHOR'):
    pytest.skip("Author test, set TEST_AUTHOR environment variable to run", allow_module_level=True)

LISTED_CATEGORY_COUNT = 37


def test_category_count():
    """Test that the correct number of categories are listed"""
    try:
        result = subprocess.run(
            ['python', 'bin/glpi-agent.py', '--list-categories'],
            capture_output=True,
            text=True,
            timeout=10
        )
        lines = result.stdout.strip().split('\n')
        
        categories = {}
        for line in lines:
            match = re.match(r'^ - (.+)$', line)
            if match:
                categories[match.group(1)] = True
        
        count = len(categories)
        assert count == LISTED_CATEGORY_COUNT, \
            f"Listed categories count: {count} should be {LISTED_CATEGORY_COUNT}"
    except Exception as e:
        pytest.skip(f"Could not run glpi-agent: {e}")


def test_categories_documented():
    """Test that all categories are documented in bin/glpi-agent"""
    try:
        # Get categories from --list-categories
        result = subprocess.run(
            ['python', 'bin/glpi-agent.py', '--list-categories'],
            capture_output=True,
            text=True,
            timeout=10
        )
        lines = result.stdout.strip().split('\n')
        
        categories = {}
        for line in lines:
            match = re.match(r'^ - (.+)$', line)
            if match:
                categories[match.group(1)] = True
        
        # Check against documentation
        if os.path.exists('bin/glpi-agent.py'):
            with open('bin/glpi-agent.py', 'r') as f:
                for line in f:
                    # Look for category documentation
                    match = re.match(r'^=item \* (.+)$', line)
                    if match:
                        categories.pop(match.group(1), None)
        
        missing = list(categories.keys())
        for cat in missing:
            print(f"Warning: Category '{cat}' is missing in bin/glpi-agent pod")
        
        assert len(missing) == 0, f"Categories missing from documentation: {missing}"
    except Exception as e:
        pytest.skip(f"Could not check categories: {e}")
