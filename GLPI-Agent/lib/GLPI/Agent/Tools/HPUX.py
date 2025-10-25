#!/usr/bin/env python3
"""
GLPI Agent Tools HPUX - Python Implementation

HPUX generic functions for system information gathering.
"""

import re
from typing import Dict, List, Optional, Any

# Import the main Tools module functions
try:
    from GLPI.Agent.Tools import get_all_lines, get_first_match
except ImportError:
    import sys
    sys.path.insert(0, '../../')
    from Tools import get_all_lines, get_first_match


__all__ = ['get_info_from_machinfo', 'is_hpvm_guest']


def get_info_from_machinfo(**params) -> Optional[Dict[str, Any]]:
    """
    Returns a structured view of machinfo output.
    
    Args:
        **params: Parameters including:
            - command: Command to run (default: /usr/contrib/bin/machinfo)
            - file: File to read instead of running command
            - logger: Logger object
            
    Returns:
        Dictionary containing parsed machinfo data
    """
    if 'command' not in params:
        params['command'] = '/usr/contrib/bin/machinfo'
    
    lines = get_all_lines(**params)
    if not lines:
        return None
    
    info = {}
    current = None
    
    for line in lines:
        # key: value (no leading space)
        match = re.match(r'^(\S[^:]+):\s+(.*\S)', line)
        if match:
            info[match.group(1)] = match.group(2)
            continue
        
        #  key: value (with leading space)
        match = re.match(r'^\s+(\S[^:]+):\s+(.*\S)', line)
        if match:
            if current and isinstance(info.get(current), dict):
                info[current][match.group(1).lower()] = match.group(2)
            continue
        
        #  key = value (with leading space)
        match = re.match(r'^\s+(\S[^=]+)\s+=\s+(.*\S)', line)
        if match:
            if current and isinstance(info.get(current), dict):
                info[current][match.group(1).lower()] = match.group(2)
            continue
        
        #  value (with leading space)
        match = re.match(r'^\s+(.*\S)', line)
        if match:
            # hack for CPUinfo:
            # accumulate new lines if current node is not a dict
            if current and current in info:
                if not isinstance(info[current], dict):
                    info[current] += " " + match.group(1)
            elif current:
                info[current] = match.group(1)
            continue
        
        # key: (section header)
        match = re.match(r'^(\S[^:]+):$', line)
        if match:
            current = match.group(1)
            # Initialize as dict for potential sub-keys
            if current not in info:
                info[current] = {}
            continue
    
    return info


def is_hpvm_guest(**params) -> Optional[str]:
    """
    Check if system is an HPVM guest.
    
    Args:
        **params: Parameters including:
            - command: Command to run (default: hpvminfo)
            - logger: Logger object
            
    Returns:
        Matched string if HPVM guest, None otherwise
    """
    if 'command' not in params:
        params['command'] = 'hpvminfo'
    
    if 'pattern' not in params:
        params['pattern'] = re.compile(r'HPVM guest')
    
    return get_first_match(**params)


if __name__ == '__main__':
    print("GLPI Agent Tools HPUX Module")
    print("HPUX generic functions")
