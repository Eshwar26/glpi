#!/usr/bin/env python3
"""Win32API::Registry fake module for non-Windows platforms"""

# Registry value types
REG_NONE = 0
REG_SZ = 1
REG_EXPAND_SZ = 2
REG_BINARY = 3
REG_DWORD = 4
REG_DWORD_BIG_ENDIAN = 5
REG_LINK = 6
REG_MULTI_SZ = 7
REG_RESOURCE_LIST = 8
REG_FULL_RESOURCE_DESCRIPTOR = 9
REG_RESOURCE_REQUIREMENTS_LIST = 10
REG_QWORD = 11

# Map constant names to values
_CONSTANTS = {
    'REG_NONE': REG_NONE,
    'REG_SZ': REG_SZ,
    'REG_EXPAND_SZ': REG_EXPAND_SZ,
    'REG_BINARY': REG_BINARY,
    'REG_DWORD': REG_DWORD,
    'REG_DWORD_BIG_ENDIAN': REG_DWORD_BIG_ENDIAN,
    'REG_LINK': REG_LINK,
    'REG_MULTI_SZ': REG_MULTI_SZ,
    'REG_RESOURCE_LIST': REG_RESOURCE_LIST,
    'REG_FULL_RESOURCE_DESCRIPTOR': REG_FULL_RESOURCE_DESCRIPTOR,
    'REG_RESOURCE_REQUIREMENTS_LIST': REG_RESOURCE_REQUIREMENTS_LIST,
    'REG_QWORD': REG_QWORD,
}


def constant(constant_name: str):
    """
    Get registry constant value.
    
    Args:
        constant_name: Name of the constant
        
    Returns:
        Constant value or None if not found
    """
    return _CONSTANTS.get(constant_name)


def RegQueryValueExW(*args, **kwargs):
    """Mock RegQueryValueExW function - no-op"""
    return None


__all__ = [
    'REG_NONE', 'REG_SZ', 'REG_EXPAND_SZ', 'REG_BINARY',
    'REG_DWORD', 'REG_DWORD_BIG_ENDIAN', 'REG_LINK', 'REG_MULTI_SZ',
    'REG_RESOURCE_LIST', 'REG_FULL_RESOURCE_DESCRIPTOR',
    'REG_RESOURCE_REQUIREMENTS_LIST', 'REG_QWORD',
    'constant', 'RegQueryValueExW',
]
