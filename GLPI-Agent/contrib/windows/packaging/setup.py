#!/usr/bin/env python3
"""setup - Setup module for Windows packaging"""

import os
import sys
from pathlib import Path

# Calculate base folder
_this_file = Path(__file__).resolve()
_basefolder = _this_file.parent.parent.parent

# Setup paths
setup = {
    'datadir': str(_basefolder / 'share'),
    'vardir': str(_basefolder / 'var'),
    'libdir': str(_basefolder / 'perl' / 'agent'),
}

# Set DLL directory on Windows
if sys.platform == 'win32':
    try:
        import ctypes
        from ctypes import wintypes
        
        kernel32 = ctypes.windll.kernel32
        
        # Define SetDllDirectory function
        SetDllDirectory = kernel32.SetDllDirectoryA
        SetDllDirectory.argtypes = [wintypes.LPCSTR]
        SetDllDirectory.restype = wintypes.BOOL
        
        # Call SetDllDirectory with perl/bin path
        dll_path = str(_basefolder / 'perl' / 'bin')
        SetDllDirectory(dll_path.encode('utf-8'))
    except (ImportError, AttributeError, OSError):
        # If SetDllDirectory is not available, skip
        pass

__all__ = ['setup']

