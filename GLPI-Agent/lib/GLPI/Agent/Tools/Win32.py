#!/usr/bin/env python3
"""
GLPI Agent Tools Win32 - Python Implementation

Windows-specific functions for system information and WMI access.

NOTE: This module requires Windows environment and Windows-specific libraries.
Full functionality requires: wmi, win32api, win32com, pywin32, etc.
"""

import re
import platform
from typing import List, Dict, Optional, Any

__all__ = [
    'get_wmi_objects',
    'get_registry_key',
    'run_powershell',
    'get_local_codepage',
    'encode_from_registry',
    'is_windows',
    'get_os_version'
]


def is_windows() -> bool:
    """Check if running on Windows."""
    return platform.system() == 'Windows'


def get_wmi_objects(**params) -> List[Dict]:
    """
    Get WMI objects using WQL query.
    
    Args:
        **params: Parameters including:
            - query: WQL query string
            - moniker: WMI moniker (optional)
            - properties: List of properties to retrieve
            - logger: Logger object
            
    Returns:
        List of object dictionaries
    """
    if not is_windows():
        return []
    
    query = params.get('query')
    if not query:
        return []
    
    objects = []
    
    try:
        # Try to use wmi module
        import wmi
        
        c = wmi.WMI()
        
        # Execute query
        results = c.query(query)
        
        properties = params.get('properties', [])
        
        for result in results:
            obj = {}
            if properties:
                for prop in properties:
                    try:
                        obj[prop] = getattr(result, prop, None)
                    except Exception:
                        obj[prop] = None
            else:
                # Get all properties
                for prop in result.properties:
                    try:
                        obj[prop] = getattr(result, prop, None)
                    except Exception:
                        obj[prop] = None
            
            objects.append(obj)
    
    except ImportError:
        logger = params.get('logger')
        if logger:
            logger.error("WMI module not available")
    except Exception as e:
        logger = params.get('logger')
        if logger:
            logger.error(f"WMI query failed: {e}")
    
    return objects


def get_registry_key(**params) -> Optional[Dict]:
    """
    Get Windows registry key values.
    
    Args:
        **params: Parameters including:
            - path: Registry path (e.g., "HKEY_LOCAL_MACHINE\\Software\\...")
            - required: List of required value names
            - logger: Logger object
            
    Returns:
        Dictionary of registry values or None
    """
    if not is_windows():
        return None
    
    path = params.get('path')
    if not path:
        return None
    
    values = {}
    
    try:
        import winreg
        
        # Parse registry path
        hive_map = {
            'HKEY_LOCAL_MACHINE': winreg.HKEY_LOCAL_MACHINE,
            'HKEY_CURRENT_USER': winreg.HKEY_CURRENT_USER,
            'HKEY_CLASSES_ROOT': winreg.HKEY_CLASSES_ROOT,
            'HKEY_USERS': winreg.HKEY_USERS,
            'HKEY_CURRENT_CONFIG': winreg.HKEY_CURRENT_CONFIG,
        }
        
        # Split path into hive and subkey
        parts = path.replace('/', '\\').split('\\', 1)
        if len(parts) < 2:
            return None
        
        hive_name = parts[0]
        subkey = parts[1]
        
        hive = hive_map.get(hive_name)
        if not hive:
            return None
        
        # Open registry key
        key = winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ)
        
        # Get all values
        i = 0
        while True:
            try:
                name, value, _ = winreg.EnumValue(key, i)
                values[f'/{name}'] = value
                i += 1
            except OSError:
                break
        
        winreg.CloseKey(key)
    
    except ImportError:
        logger = params.get('logger')
        if logger:
            logger.error("winreg module not available")
    except Exception as e:
        logger = params.get('logger')
        if logger:
            logger.debug(f"Registry key read failed: {e}")
    
    return values if values else None


def run_powershell(**params) -> Optional[List[str]]:
    """
    Run PowerShell script and return output.
    
    Args:
        **params: Parameters including:
            - script: PowerShell script string
            - logger: Logger object
            
    Returns:
        List of output lines or None
    """
    if not is_windows():
        return None
    
    script = params.get('script')
    if not script:
        return None
    
    try:
        import subprocess
        
        # Run PowerShell
        result = subprocess.run(
            ['powershell', '-NoProfile', '-NonInteractive', '-Command', script],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return result.stdout.strip().split('\n')
        
    except Exception as e:
        logger = params.get('logger')
        if logger:
            logger.error(f"PowerShell execution failed: {e}")
    
    return None


def get_local_codepage() -> str:
    """
    Get local system codepage.
    
    Returns:
        Codepage name (e.g., 'cp1252', 'utf-8')
    """
    if not is_windows():
        return 'utf-8'
    
    try:
        import locale
        return locale.getpreferredencoding()
    except Exception:
        return 'cp1252'  # Default Windows codepage


def encode_from_registry(value: str) -> str:
    """
    Encode string from registry encoding to UTF-8.
    
    Args:
        value: String from registry
        
    Returns:
        UTF-8 encoded string
    """
    if not value:
        return value
    
    codepage = get_local_codepage()
    
    try:
        if isinstance(value, bytes):
            return value.decode(codepage, errors='ignore')
        return value
    except Exception:
        return value


def get_os_version() -> Optional[Dict]:
    """
    Get Windows OS version information.
    
    Returns:
        Dictionary with OS version details
    """
    if not is_windows():
        return None
    
    version_info = {}
    
    try:
        import sys
        version_info['platform'] = sys.platform
        version_info['version'] = platform.version()
        version_info['release'] = platform.release()
        
        # Try to get more detailed Windows version
        if hasattr(sys, 'getwindowsversion'):
            win_ver = sys.getwindowsversion()
            version_info['major'] = win_ver.major
            version_info['minor'] = win_ver.minor
            version_info['build'] = win_ver.build
    
    except Exception:
        pass
    
    return version_info


if __name__ == '__main__':
    print("GLPI Agent Tools Win32 Module")
    print(f"Running on Windows: {is_windows()}")
    print(f"Local codepage: {get_local_codepage()}")
