#!/usr/bin/env python3

import os
import re
import pytest

# Skip test if not running author tests
if not os.environ.get('TEST_AUTHOR'):
    pytest.skip("Author test, set TEST_AUTHOR environment variable to run", allow_module_level=True)


def test_whitespace_issues():
    """Test for whitespace issues in source files"""
    dirs = ['lib', 'bin', 't']
    ignore_patterns = [r'~$', r'mock\.py$', r'cisco\.py$']
    
    errors = []
    for directory in dirs:
        if not os.path.exists(directory):
            continue
        for root, _, files in os.walk(directory):
            for filename in files:
                if not filename.endswith('.py'):
                    continue
                
                # Check ignore patterns
                filepath = os.path.join(root, filename)
                if any(re.search(pattern, filepath) for pattern in ignore_patterns):
                    continue
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        for line_num, line in enumerate(f, 1):
                            # Check for trailing whitespace
                            if line.rstrip('\n').endswith((' ', '\t')):
                                errors.append(f"{filepath}:{line_num}: trailing whitespace")
                            # Check for tabs (Python style guide prefers spaces)
                            if '\t' in line and filepath.endswith('.py'):
                                errors.append(f"{filepath}:{line_num}: contains tabs")
                except Exception as e:
                    errors.append(f"{filepath}: could not read - {e}")
    
    assert not errors, "Whitespace issues found:\n" + "\n".join(errors[:20])
