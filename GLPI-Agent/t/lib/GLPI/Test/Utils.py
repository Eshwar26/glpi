#!/usr/bin/env python3
"""Test Utils Module - Utility functions for testing"""

import os
import sys
import re
import socket
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Any, Callable
import platform

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'lib'))


def test_port(port: int) -> bool:
    """
    Test if a port is available.
    
    Args:
        port: Port number to test
        
    Returns:
        True if port is available, False otherwise
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(('localhost', port))
            return True
    except (OSError, socket.error):
        return False


def mockGetWMIObjects(test: str) -> Callable:
    """
    Create a mock function for GetWMIObjects.
    
    Args:
        test: Test name prefix for WMI dump files
        
    Returns:
        Mock function that loads WMI dumps from files
    """
    def mock_getwmi(**params) -> List[Dict[str, Any]]:
        """Mock GetWMIObjects function"""
        class_name = params.get('class')
        
        if not class_name:
            query = params.get('query')
            if isinstance(query, list) and query:
                query = query[0]
            if isinstance(query, str):
                match = re.search(r'FROM\s+(\w+)', query, re.IGNORECASE)
                if match:
                    class_name = match.group(1)
        
        if not class_name:
            return []
        
        file = f"resources/win32/wmi/{test}-{class_name}.wmi"
        properties = params.get('properties', [])
        return loadWMIDump(file, properties)
    
    return mock_getwmi


def loadWMIDump(file: str, properties: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Load WMI dump from file.
    
    Args:
        file: Path to WMI dump file
        properties: List of property names to extract
        
    Returns:
        List of objects with extracted properties
    """
    if properties is None:
        properties = []
    
    if not os.path.exists(file):
        return []
    
    # Build set of desired properties
    properties_set = set(properties)
    
    objects = []
    current_object = None
    
    try:
        # Windows files are UTF-16LE encoded
        with open(file, 'r', encoding='utf-16le', newline='\r\n') as f:
            for line in f:
                line = line.rstrip('\r\n')
                
                # Skip comments
                if line.startswith('#'):
                    continue
                
                # Match property assignment: " Property = Value "
                match = re.match(r'^\s*(\w+)\s*=\s*(.+)\s*$', line)
                if match:
                    key = match.group(1)
                    value = match.group(2).strip()
                    
                    # Skip if property not requested
                    if properties and key not in properties_set:
                        continue
                    
                    if current_object is None:
                        current_object = {}
                    
                    # Handle list values: { "value1", "value2" }
                    list_match = re.match(r'\{(".*")\}', value)
                    if list_match:
                        values_str = list_match.group(1)
                        values = [m.group(1) for m in re.finditer(r'"([^"]+)"', values_str)]
                        current_object[key] = values
                    else:
                        # Replace HTML entities
                        value = value.replace('&amp;', '&')
                        current_object[key] = value
                    continue
                
                # Empty line indicates end of object
                if not line.strip():
                    if current_object:
                        objects.append(current_object)
                        current_object = None
                    continue
            
            # Add last object if exists
            if current_object:
                objects.append(current_object)
    
    except (IOError, UnicodeDecodeError):
        return []
    
    return objects


def mockGetRegistryKey(test: str) -> Callable:
    """
    Create a mock function for GetRegistryKey.
    
    Args:
        test: Test name prefix for registry dump files
        
    Returns:
        Mock function that loads registry dumps from files
    """
    def mock_getregistrykey(**params) -> Any:
        """Mock GetRegistryKey function"""
        path = params.get('path') or params.get('keyName')
        if not path:
            return None
        
        # Get last element of path
        path_parts = path.replace('\\', '/').split('/')
        last_element = path_parts[-1] if path_parts else ''
        
        file = f"resources/win32/registry/{test}-{last_element}.reg"
        return loadRegistryDump(file)
    
    return mock_getregistrykey


def loadRegistryDump(file: str) -> Dict[str, Any]:
    """
    Load registry dump from file.
    
    Args:
        file: Path to registry dump file
        
    Returns:
        Dictionary representing registry structure
    """
    if not os.path.exists(file):
        return {}
    
    root_key = {}
    root_offset = None
    current_key = root_key
    current_variable = None
    
    try:
        # Windows files are UTF-16LE encoded
        with open(file, 'r', encoding='utf-16le', newline='\r\n') as f:
            for line in f:
                line = line.rstrip('\r\n')
                
                # Match registry key: [ HKEY_LOCAL_MACHINE\... ]
                match = re.match(r'^\s*\[([^\]]+)\]\s*$', line)
                if match:
                    path = match.group(1)
                    path_parts = path.split('\\')
                    
                    if root_offset is None:
                        root_offset = len(path_parts)
                    
                    # Adjust path by root offset
                    if root_offset:
                        path_parts = path_parts[root_offset:]
                        current_key = root_key
                    
                    # Navigate/create path
                    for element in path_parts:
                        key_path = element + '/'
                        if key_path not in current_key:
                            current_key[key_path] = {}
                        current_key = current_key[key_path]
                    continue
                
                # Match DWORD value: "Key" = dword:12345678
                match = re.match(r'^\s*"([^"]+)"\s*=\s*dword:([0-9a-f]+)', line)
                if match:
                    key = match.group(1)
                    value = match.group(2)
                    current_key['/' + key] = f"0x{value}"
                    continue
                
                # Match hex/QWORD value: "Key" = hex:12,34,56,78
                match = re.match(r'^\s*"([^"]+)"\s*=\s*hex(?:\(b\))?:([a-f0-9,]+)', line)
                if match:
                    key = match.group(1)
                    value = match.group(2)
                    current_key['/' + key] = _binary(value)
                    current_variable = '/' + key if line.endswith('\\') else None
                    continue
                
                # Match string value: "Key" = "Value"
                match = re.match(r'^\s*"([^"]+)"\s*=\s*"([^"]*)"', line)
                if match:
                    key = match.group(1)
                    value = match.group(2).replace('\\\\', '\\')
                    current_key['/' + key] = value
                    continue
                
                # Match default key value: @ = "Value"
                match = re.match(r'^\s*@\s*=\s*"([^"]*)"', line)
                if match:
                    value = match.group(1).replace('\\\\', '\\')
                    current_key['/'] = value
                    continue
                
                # Continuation line for hex data
                match = re.match(r'^\s\s([a-f0-9,]+)', line)
                if match and current_variable:
                    value = match.group(1)
                    current_key[current_variable] += _binary(value)
                    if not line.endswith('\\'):
                        current_variable = None
    
    except (IOError, UnicodeDecodeError):
        return {}
    
    return root_key


def _binary(string: str) -> bytes:
    """
    Convert hex string to binary.
    
    Args:
        string: Comma-separated hex values (e.g., "12,34,56,78")
        
    Returns:
        Binary data as bytes
    """
    values = [int(x, 16) for x in string.split(',') if x.strip()]
    return bytes(values)


def unsetProxyEnvVar():
    """Unset proxy environment variables"""
    for key in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
        if key in os.environ:
            del os.environ[key]


def run_executable(executable: str, args: Optional[str] = None) -> tuple:
    """
    Run an executable with arguments.
    
    Args:
        executable: Executable name (relative to bin/)
        args: Space-separated arguments as string
        
    Returns:
        Tuple of (stdout, stderr, return_code)
    """
    executable_path = Path(__file__).parent.parent.parent.parent / 'bin' / executable
    
    cmd = [sys.executable, str(executable_path)]
    if args:
        cmd.extend(args.split())
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        return (result.stdout, result.stderr, result.returncode)
    except Exception as e:
        return ("", str(e), 1)


def openWin32Registry():
    """
    Open Windows registry for testing (Windows only).
    
    Note: This function requires Windows and appropriate permissions.
    
    Returns:
        Registry key object
    """
    if platform.system() != 'Windows':
        raise NotImplementedError("openWin32Registry only works on Windows")
    
    try:
        import winreg
        
        agent_key = 'GLPI-Agent-unittest'
        hkey = winreg.HKEY_LOCAL_MACHINE
        
        try:
            # Try to open existing key
            settings = winreg.OpenKey(hkey, f'SOFTWARE\\{agent_key}', 0, winreg.KEY_READ | winreg.KEY_WRITE)
            return settings
        except FileNotFoundError:
            # Create test key
            software_key = winreg.OpenKey(hkey, 'SOFTWARE', 0, winreg.KEY_WRITE)
            try:
                winreg.CreateKey(software_key, agent_key)
            finally:
                winreg.CloseKey(software_key)
            
            # Open the created key
            settings = winreg.OpenKey(hkey, f'SOFTWARE\\{agent_key}', 0, winreg.KEY_READ | winreg.KEY_WRITE)
            return settings
    
    except Exception as e:
        raise RuntimeError(
            f"Failed to open HKEY_LOCAL_MACHINE hive, "
            f"be sure to run this win32 test with Administrator privileges: {e}"
        )
