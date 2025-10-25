#!/usr/bin/env python3
"""
Batch convert Perl test files to Python stub tests
"""

import os
import sys
from pathlib import Path


PYTHON_TEST_TEMPLATE = '''#!/usr/bin/env python3
"""
{docstring}

NOTE: This test was automatically converted from Perl.
      Manual review and completion is required.
"""

import os
import sys
import platform
import re
import pytest
{extra_imports}
# Add paths
sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')

{skip_section}

def test_needs_manual_conversion():
    """
    This test was automatically converted from Perl to Python.
    The original test logic needs to be manually reviewed and implemented.
    
    Original file: {original_file}
    """
    pytest.skip("Test requires manual conversion from Perl to Python")
    

# TODO: Review original Perl test and implement Python equivalent
# Original Perl code preserved below for reference:
"""
{original_content}
"""
'''


def convert_file(filepath):
    """Convert a single Perl test file to Python stub"""
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return False
    
    # Check if already converted
    if 'import pytest' in content and 'def test_' in content:
        return False  # Already converted
    
    # Check if this is Perl
    if not ('#!/usr/bin/perl' in content or 'use strict' in content):
        return False  # Not a Perl file
    
    # Determine extra imports needed
    extra_imports = []
    if 'tempdir' in content.lower() or 'file::temp' in content.lower():
        extra_imports.append('import tempfile')
    if 'json' in content.lower():
        extra_imports.append('import json')
    if 'subprocess' in content.lower() or 'system(' in content:
        extra_imports.append('import subprocess')
    
    extra_imports_str = '\n'.join(extra_imports)
    if extra_imports_str:
        extra_imports_str = '\n' + extra_imports_str
    
    # Check for skip_all
    skip_section = ''
    if 'TEST_AUTHOR' in content:
        skip_section = '''# Skip test if not running author tests
if not os.environ.get('TEST_AUTHOR'):
    pytest.skip("Author test, set TEST_AUTHOR environment variable to run", allow_module_level=True)
'''
    
    # Generate docstring
    rel_path = str(Path(filepath).relative_to(Path.cwd()))
    docstring = f"Test module converted from {rel_path}"
    
    # Truncate original content for comment (keep it reasonable)
    original_lines = content.split('\n')
    if len(original_lines) > 100:
        original_content = '\n'.join(original_lines[:100]) + '\n\n... (truncated, see git history for full original)'
    else:
        original_content = content
    
    # Generate Python test
    python_content = PYTHON_TEST_TEMPLATE.format(
        docstring=docstring,
        extra_imports=extra_imports_str,
        skip_section=skip_section,
        original_file=rel_path,
        original_content=original_content
    )
    
    # Write converted file
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(python_content)
        return True
    except Exception as e:
        print(f"Error writing {filepath}: {e}")
        return False


def main():
    """Main conversion function"""
    
    # Find all .py files in t/ directory
    t_dir = Path('t')
    if not t_dir.exists():
        print("Error: t/ directory not found")
        print("Run this script from the GLPI-Agent root directory")
        return 1
    
    py_files = list(t_dir.rglob('*.py'))
    print(f"Found {len(py_files)} .py files in t/ directory")
    
    converted = 0
    skipped = 0
    errors = 0
    
    for filepath in sorted(py_files):
        result = convert_file(filepath)
        if result:
            converted += 1
            print(f"✓ Converted: {filepath}")
        elif result is False:
            skipped += 1
        else:
            errors += 1
            print(f"✗ Error: {filepath}")
    
    print(f"\n{'='*60}")
    print(f"Conversion Summary:")
    print(f"  Converted: {converted}")
    print(f"  Skipped:   {skipped}")
    print(f"  Errors:    {errors}")
    print(f"  Total:     {len(py_files)}")
    print(f"{'='*60}")
    print(f"\nNote: Converted files are stubs that skip tests.")
    print(f"      Manual review and implementation is required.")
    
    return 0


if __name__ == '__main__':
    # Change to GLPI-Agent directory if we're in tools/
    if Path.cwd().name == 'tools':
        os.chdir('..')
    
    sys.exit(main())

