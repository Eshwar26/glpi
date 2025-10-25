#!/usr/bin/env python3

import os
import sys
import platform
import glob
import py_compile
import pytest

# Add mock modules for non-available ones
if platform.system() == 'Windows':
    sys.path.insert(0, 't/lib/fake/unix')
else:
    sys.path.insert(0, 't/lib/fake/windows')


def get_all_py_files(directory):
    """Get all Python files in a directory recursively"""
    py_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                py_files.append(os.path.join(root, file))
    return py_files


def filter_file(filepath):
    """Filter files based on platform and dependencies"""
    # On non-Windows, skip Windows-specific files
    if platform.system() != 'Windows':
        if 'Agent/Tools/Win32' in filepath:
            return False
        if 'Agent/Daemon/Win32' in filepath:
            return False
        if 'Agent/Task/Inventory/Win32' in filepath:
            return False
    
    return True


def test_all_modules_compile():
    """Test that all Python modules compile successfully"""
    files = get_all_py_files('lib')
    
    # On Linux, include installer modules
    if platform.system() == 'Linux':
        sys.path.insert(0, 'contrib/unix/installer')
        files.extend(get_all_py_files('contrib/unix/installer'))
    
    # Filter files
    files = [f for f in files if filter_file(f)]
    
    errors = []
    for filepath in files:
        try:
            py_compile.compile(filepath, doraise=True)
        except py_compile.PyCompileError as e:
            errors.append(f"{filepath}: {e}")
    
    assert not errors, f"Compilation errors:\n" + "\n".join(errors)
