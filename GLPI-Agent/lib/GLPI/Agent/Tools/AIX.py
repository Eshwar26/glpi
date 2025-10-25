#!/usr/bin/env python3
"""
GLPI Agent AIX Tools - Python Implementation

This module provides AIX-specific generic functions for the GLPI Agent.
"""

from typing import Dict, List, Optional, Any
import re

# Import the main Tools module functions
try:
    from GLPI.Agent.Tools import get_all_lines
except ImportError:
    # For testing, allow standalone usage
    import sys
    sys.path.insert(0, '../../')
    from Tools import get_all_lines


__all__ = [
    'get_lsvpd_infos',
    'get_lsconf_infos',
    'get_adapters_from_lsdev'
]


def get_lsvpd_infos(**params) -> List[Dict[str, str]]:
    """
    Get vital product data information from lsvpd command.
    
    Args:
        **params: Optional parameters including:
            - command: Command to execute (default: 'lsvpd')
            - file: File to read from instead of running command
            - logger: Logger object
            
    Returns:
        List of dictionaries containing vital product data info
        
    Example output:
        [
            {
                'DS': 'System VPD',
                'YL': 'U9111.520.65DEDAB',
                'RT': 'VSYS',
                'FG': 'XXSV',
                'BR': 'O0',
                'SE': '65DEDAB',
                'TM': '9111-520',
                'SU': '0004AC0BA763',
                'VK': 'ipzSeries'
            },
            ...
        ]
    """
    # Set default command if not specified
    if 'command' not in params:
        params['command'] = 'lsvpd'
    
    lines = get_all_lines(**params)
    if not lines:
        return []
    
    devices = []
    device = {}
    
    # Skip first lines until we find the first block delimiter
    while lines:
        line = lines.pop(0)
        if re.match(r'^\*FC \?+', line):
            break
    
    # Process remaining lines
    for line in lines:
        if re.match(r'^\*FC \?+', line):
            # Block delimiter - save current device and start new one
            if device:
                devices.append(device)
                device = {}
            continue
        
        # Parse key-value pairs
        match = re.match(r'^\* ([A-Z]{2}) \s+ (.*\S)', line, re.VERBOSE)
        if match:
            key = match.group(1)
            value = match.group(2)
            device[key] = value
    
    # Don't forget last device
    if device:
        devices.append(device)
    
    return devices


def get_lsconf_infos(**params) -> Dict[str, Any]:
    """
    Get system configuration information from lsconf command.
    
    Args:
        **params: Optional parameters including:
            - command: Command to execute (default: 'lsconf')
            - file: File to read from instead of running command
            - logger: Logger object
            
    Returns:
        Dictionary containing configuration information
    """
    # Set default command if not specified
    if 'command' not in params:
        params['command'] = 'lsconf'
    
    lines = get_all_lines(**params)
    if not lines:
        return {}
    
    infos = {}
    key = None
    
    for line in lines:
        # Remove carriage return
        line = line.rstrip('\r')
        
        # Match pattern: "key : value"
        match = re.match(r'^(\S[^:]+) : \s+ (.+) \s*$', line, re.VERBOSE)
        if match:
            top_key = match.group(1)
            value = match.group(2)
            infos[top_key] = value
        
        # Empty line - reset key context
        elif re.match(r'^\s*$', line):
            key = None
        
        # Nested key-value pair (indented)
        elif key and re.match(r'^\s+ (\S[^:]+) : \s+ (.+) \s*$', line, re.VERBOSE):
            match = re.match(r'^\s+ (\S[^:]+) : \s+ (.+) \s*$', line, re.VERBOSE)
            if match:
                nested_key = match.group(1)
                value = match.group(2)
                if not isinstance(infos.get(key), dict):
                    infos[key] = {}
                infos[key][nested_key] = value
        
        # Start of new section (non-indented line without colon)
        elif not key and re.match(r'^\S', line):
            key = line.strip()
    
    return infos


def get_adapters_from_lsdev(**params) -> List[Dict[str, str]]:
    """
    Get list of adapters from lsdev command.
    
    Args:
        **params: Optional parameters including:
            - command: Command to execute (default: 'lsdev -Cc adapter -F "name:type:description"')
            - file: File to read from instead of running command
            - logger: Logger object
            
    Returns:
        List of dictionaries containing adapter information
        
    Example output:
        [
            {
                'NAME': 'ent0',
                'TYPE': 'ethernet',
                'DESCRIPTION': 'Ethernet Adapter'
            },
            ...
        ]
    """
    # Set default command if not specified
    if 'command' not in params:
        params['command'] = 'lsdev -Cc adapter -F "name:type:description"'
    
    lines = get_all_lines(**params)
    if not lines:
        return []
    
    adapters = []
    
    for line in lines:
        info = line.split(':')
        if len(info) >= 3:
            adapters.append({
                'NAME': info[0],
                'TYPE': info[1],
                'DESCRIPTION': info[2]
            })
    
    return adapters


if __name__ == '__main__':
    # Basic testing
    print("GLPI Agent AIX Tools")
    print("Available functions:")
    for func in __all__:
        print(f"  - {func}")
