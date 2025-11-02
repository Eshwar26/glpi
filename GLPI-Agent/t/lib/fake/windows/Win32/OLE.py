#!/usr/bin/env python3
"""Win32::OLE fake module for non-Windows platforms"""

# Constants
CP_UTF8 = 0

# Mock constants for OLE
VT_BYREF = None
VT_BSTR = None


def in_func():
    """Mock 'in' function"""
    pass


def Option(*args, **kwargs):
    """Mock Option function"""
    pass


# Module-level exports for compatibility
__all__ = ['CP_UTF8', 'VT_BYREF', 'VT_BSTR', 'in_func', 'Option']
