"""
GLPI Agent Setup Module

This module provides configuration paths for the GLPI Agent installation.
It automatically determines absolute paths for library, data, and variable directories
based on the module's installation location.

The setup dictionary is exported and can be imported by other modules to access
standardized directory paths.
"""

import os
import sys
import platform
from pathlib import Path
from typing import Dict


# Setup configuration dictionary - exported for use by other modules
setup: Dict[str, str] = {
    'datadir': './share',
    'libdir': './lib',
    'vardir': './var',
}


def _initialize_setup():
    """
    Initialize the setup configuration with absolute paths.
    
    This function computes the library directory based on this file's location
    and resolves relative paths for data and variable directories.
    """
    global setup
    
    try:
        # Compute libdir from this setup file's location
        # It should be installed in the expected directory
        current_file = Path(__file__).resolve()
        
        if not setup['libdir'] or not Path(setup['libdir']).is_absolute():
            setup['libdir'] = str(current_file.parent)
        
        # If we have an absolute libdir, rebase other paths relative to it
        if Path(setup['libdir']).is_absolute():
            libdir_parent = Path(setup['libdir']).parent
            
            for key in ['datadir', 'vardir']:
                # Don't update if target is already absolute
                if setup[key] and Path(setup[key]).is_absolute():
                    continue
                
                # Resolve path relative to libdir's parent
                folder = (libdir_parent / setup[key]).resolve()
                
                # Only update if the folder exists
                if folder.exists() and folder.is_dir():
                    setup[key] = str(folder)
    
    except Exception as e:
        # Silently handle errors to match Perl's eval behavior
        # In production, you might want to log this
        pass


def _set_dll_directory_windows():
    """
    Set the DLL search directory on Windows platforms.
    
    This ensures that required DLLs can be found by setting the DLL directory
    to the Python executable's location.
    """
    if platform.system() == 'Windows':
        try:
            import ctypes
            from ctypes import wintypes
            
            # Load kernel32.dll
            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
            
            # Define SetDllDirectoryA function signature
            # BOOL SetDllDirectoryA(LPCSTR lpPathName)
            kernel32.SetDllDirectoryA.argtypes = [wintypes.LPCSTR]
            kernel32.SetDllDirectoryA.restype = wintypes.BOOL
            
            # Get Python executable directory
            python_dir = os.path.dirname(sys.executable)
            
            # Call SetDllDirectoryA with the Python directory
            kernel32.SetDllDirectoryA(python_dir.encode('ascii'))
            
        except (ImportError, OSError, AttributeError) as e:
            # Silently handle errors if ctypes or the API is unavailable
            # In production, you might want to log this
            pass


# Initialize setup when module is imported
_initialize_setup()
_set_dll_directory_windows()


# Export setup dictionary for use by other modules
__all__ = ['setup']


# Helper functions for accessing setup paths
def get_libdir() -> str:
    """
    Get the library directory path.
    
    Returns:
        Absolute path to the library directory
    """
    return setup['libdir']


def get_datadir() -> str:
    """
    Get the data directory path.
    
    Returns:
        Path to the data directory (may be relative)
    """
    return setup['datadir']


def get_vardir() -> str:
    """
    Get the variable directory path.
    
    Returns:
        Path to the variable directory (may be relative)
    """
    return setup['vardir']


def get_setup() -> Dict[str, str]:
    """
    Get a copy of the complete setup configuration.
    
    Returns:
        Dictionary containing all setup paths
    """
    return setup.copy()


# Example usage and testing
if __name__ == "__main__":
    print("GLPI Agent Setup Configuration")
    print("=" * 50)
    print(f"Library Directory: {setup['libdir']}")
    print(f"Data Directory:    {setup['datadir']}")
    print(f"Variable Directory: {setup['vardir']}")
    print()
    
    # Check if paths are absolute
    print("Path Types:")
    print(f"  libdir is absolute:  {Path(setup['libdir']).is_absolute()}")
    print(f"  datadir is absolute: {Path(setup['datadir']).is_absolute()}")
    print(f"  vardir is absolute:  {Path(setup['vardir']).is_absolute()}")
    print()
    
    # Show which paths exist
    print("Path Existence:")
    for key, path in setup.items():
        exists = Path(path).exists()
        print(f"  {key}: {exists}")
    print()
    
    # Platform information
    print(f"Platform: {platform.system()}")
    print(f"Python Executable: {sys.executable}")