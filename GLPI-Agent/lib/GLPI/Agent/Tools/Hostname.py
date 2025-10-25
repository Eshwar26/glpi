#!/usr/bin/env python3
"""
GLPI Agent Hostname Tools - Python Implementation

This module provides OS-independent hostname computing functions.
"""

import socket
import platform
import os
import re
from typing import Optional

# Import the main Tools module functions
try:
    from GLPI.Agent.Tools import get_first_line, empty, _remote
except ImportError:
    import sys
    sys.path.insert(0, '../../')
    from Tools import get_first_line, empty, _remote


__all__ = [
    'get_hostname',
    'get_remote_fqdn',
    'get_remote_hostdomain'
]


def get_hostname(fqdn: bool = False, short: bool = False) -> Optional[str]:
    """
    Get the hostname of the system.
    
    Args:
        fqdn: Return fully qualified domain name if True
        short: Return short hostname (without domain) if True
        
    Returns:
        Hostname string
    """
    hostname = None
    
    if _remote:
        if fqdn:
            hostname = _remote.getRemoteFQDN()
            if hostname:
                # Remove trailing dot
                hostname = hostname.rstrip('.')
        
        # Fallback on getRemoteHostname if fqdn was requested and failed
        if not hostname or empty(hostname):
            hostname = _remote.getRemoteHostname()
    else:
        if platform.system() == 'Windows':
            hostname = _get_hostname_windows()
        else:
            hostname = _get_hostname_unix(fqdn=fqdn)
    
    # Support short hostname option
    if short and hostname:
        hostname = re.sub(r'\..*$', '', hostname)
    
    return hostname


def _get_hostname_unix(fqdn: bool = False) -> Optional[str]:
    """
    Get hostname on Unix-like systems.
    
    Args:
        fqdn: Return fully qualified domain name if True
        
    Returns:
        Hostname string
    """
    hostname = None
    
    if fqdn:
        # On Linux, try hostname command first as it's more accurate
        if platform.system() == 'Linux':
            fqdn_hostname = get_first_line(command='hostname -f')
            if not empty(fqdn_hostname):
                return fqdn_hostname
        
        # Fallback to socket.getfqdn()
        try:
            fqdn_hostname = socket.getfqdn()
            if not empty(fqdn_hostname):
                # Remove trailing dot if present
                hostname = fqdn_hostname.rstrip('.')
        except Exception:
            pass
    
    # Get regular hostname if FQDN not requested or failed
    if not hostname:
        try:
            hostname = socket.gethostname()
        except Exception:
            pass
    
    return hostname


def _get_hostname_windows() -> Optional[str]:
    """
    Get hostname on Windows systems.
    
    Returns:
        Hostname string
    """
    # Try to import Windows-specific modules
    try:
        import ctypes
        from ctypes import wintypes
        
        # ComputerNamePhysicalDnsFullyQualified = 3
        GetComputerNameExW = ctypes.windll.kernel32.GetComputerNameExW
        GetComputerNameExW.argtypes = [wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        GetComputerNameExW.restype = wintypes.BOOL
        
        buffer_size = wintypes.DWORD(1024)
        buffer = ctypes.create_unicode_buffer(buffer_size.value)
        
        success = GetComputerNameExW(3, buffer, ctypes.byref(buffer_size))
        
        if success:
            hostname = buffer.value
            if hostname:
                return hostname
    except Exception:
        pass
    
    # Fallback to environment variable or socket
    hostname = os.environ.get('COMPUTERNAME')
    if not hostname:
        try:
            hostname = socket.gethostname()
        except Exception:
            pass
    
    return hostname


def get_remote_fqdn() -> Optional[str]:
    """
    Get remote fully qualified domain name if connected to remote system.
    
    Returns:
        Remote FQDN or None
    """
    if _remote:
        return _remote.getRemoteFQDN()
    return None


def get_remote_hostdomain() -> Optional[str]:
    """
    Get remote host domain if connected to remote system.
    
    Returns:
        Remote host domain or None
    """
    if _remote:
        return _remote.getRemoteHostDomain()
    return None


if __name__ == '__main__':
    print("GLPI Agent Hostname Tools")
    print("Available functions:")
    for func in __all__:
        print(f"  - {func}")
    
    # Test functions
    print("\nTesting hostname functions:")
    print(f"  Hostname: {get_hostname()}")
    print(f"  FQDN: {get_hostname(fqdn=True)}")
    print(f"  Short: {get_hostname(short=True)}")
