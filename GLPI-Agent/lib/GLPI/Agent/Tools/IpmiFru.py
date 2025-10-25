#!/usr/bin/env python3
"""
GLPI Agent IPMI FRU Tools - Python Implementation

This module provides IPMI FRU (Field Replaceable Unit) functions.
"""

from typing import Dict, List, Optional, Any

# Import the main Tools module functions
try:
    from GLPI.Agent.Tools import get_all_lines, trim_whitespace, get_canonical_size, get_canonical_manufacturer
    from GLPI.Agent.Tools.PartNumber import PartNumberFactory
except ImportError:
    import sys
    sys.path.insert(0, '../../')
    from Tools import get_all_lines, trim_whitespace, get_canonical_size, get_canonical_manufacturer
    # Mock for standalone usage
    class PartNumberFactory:
        def __init__(self, **params):
            pass
        def match(self, **params):
            return None


__all__ = [
    'get_ipmi_fru',
    'parse_fru'
]


# FRU field mapping configuration
MAPPING = {
    'CAPACITY': {
        'src': ['Memory size'],
        'sub': get_canonical_size,
    },
    'NAME': {
        'src': ['Board Product', 'Product Name']
    },
    'MODEL': {
        'src': ['Board Part Number', 'Product Part Number', 'Part Number']
    },
    'PARTNUM': {
        'src': ['Board Part Number', 'Product Part Number', 'Part Number']
    },
    'SERIAL': {
        'src': ['Board Serial', 'Product Serial', 'Serial Number']
    },
    'SERIALNUMBER': {
        'src': ['Board Serial', 'Product Serial', 'Serial Number']
    },
    'MANUFACTURER': {
        'src': ['Board Mfg', 'Product Manufacturer', 'Manufacturer'],
        'sub': get_canonical_manufacturer
    },
    'REV': {
        'src': ['Product Version']
    },
    'POWER_MAX': {
        'src': ['Max Power Capacity']
    },
}


# Cache for FRU data
_fru_cache: Optional[Dict[str, Dict[str, str]]] = None


def get_ipmi_fru(**params) -> Optional[Dict[str, Dict[str, str]]]:
    """
    Get IPMI FRU (Field Replaceable Unit) information.
    
    Args:
        **params: Optional parameters including:
            - command: Command to execute (default: 'ipmitool fru print')
            - file: File to read from instead of running command
            - logger: Logger object
            
    Returns:
        Dictionary of FRU entries keyed by device description
        
    Example output:
        {
            'System Board': {
                'Board Mfg': 'Dell Inc.',
                'Board Product': 'PowerEdge R620',
                'Board Serial': 'ABC123',
                ...
            },
            ...
        }
    """
    global _fru_cache
    
    # Set default command if not specified
    if 'command' not in params:
        params['command'] = 'ipmitool fru print'
    
    # Clear cache if testing with file
    if 'file' in params:
        _fru_cache = None
    elif _fru_cache is not None:
        # Return cached value
        return _fru_cache
    
    lines = get_all_lines(**params)
    if not lines:
        return None
    
    fru = {}
    block = {}
    descr = None
    
    import re
    
    for line in lines:
        # Match FRU Device Description header
        match = re.match(r'^FRU Device Description : (.*)(?: \(ID (\d+)\))?', line)
        if match:
            # Start of new block - save previous block
            if block and descr:
                fru[descr] = block
                block = {}
            
            descr = match.group(1)
            continue
        
        # Skip if no description set yet
        if not descr:
            continue
        
        # Parse key-value pairs
        match = re.match(r'^\s+([^:]+\w)\s+:\s([[:print:]]+)', line)
        if match:
            key = match.group(1)
            value = trim_whitespace(match.group(2))
            block[key] = value
    
    # Don't forget last block
    if block and descr:
        fru[descr] = block
    
    # Cache the result
    _fru_cache = fru
    
    return fru


def parse_fru(fru: Dict[str, str], fields: Dict[str, Any], 
              device: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Parse FRU section into formatted device dictionary.
    
    Args:
        fru: FRU data dictionary for a single device
        fields: Dictionary of field names to extract
        device: Optional existing device dictionary to update
        
    Returns:
        Dictionary containing parsed device information
    """
    if device is None:
        device = {}
    
    # Process each requested attribute
    for attr in fields.keys():
        if attr not in MAPPING:
            continue
        
        val = MAPPING[attr]
        
        # Try each possible source field
        for src in val['src']:
            if src not in fru:
                continue
            
            # Apply transformation function if specified
            if 'sub' in val and val['sub']:
                device[attr] = val['sub'](fru[src])
            else:
                device[attr] = fru[src]
            
            break
    
    # Fix manufacturer using canonical function
    if 'MANUFACTURER' in device and device['MANUFACTURER']:
        device['MANUFACTURER'] = get_canonical_manufacturer(device['MANUFACTURER'])
    
    # Validate PartNumber (fixes Dell PartNumbers, for example)
    partnum = device.get('PARTNUM') or device.get('MODEL')
    if partnum:
        try:
            partnumber_factory = PartNumberFactory()
            partnumber = partnumber_factory.match(
                partnumber=partnum,
                manufacturer=device.get('MANUFACTURER'),
                category="controller",
            )
            
            if partnumber:
                if 'PARTNUM' in fields:
                    device['PARTNUM'] = partnumber.get()
                if 'MODEL' in fields:
                    device['MODEL'] = partnumber.get()
                if 'REV' in fields and partnumber.revision():
                    device['REV'] = partnumber.revision()
        except Exception:
            # If partnumber matching fails, just continue with original value
            pass
    
    return device


if __name__ == '__main__':
    print("GLPI Agent IPMI FRU Tools")
    print("Available functions:")
    for func in __all__:
        print(f"  - {func}")
