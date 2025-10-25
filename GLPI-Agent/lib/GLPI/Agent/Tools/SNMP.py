#!/usr/bin/env python3
"""
GLPI Agent Tools SNMP - Python Implementation

SNMP Hardware-related utility functions for cleaning and canonicalizing SNMP data.
"""

import re
from typing import Optional, List, Dict, Any, Pattern

try:
    from GLPI.Agent.Tools import hex2char, get_utf8_string, empty
except ImportError:
    # Stub implementations
    def hex2char(value):
        return value
    
    def get_utf8_string(value):
        return value
    
    def empty(value):
        return not value


__all__ = [
    'get_canonical_serial_number',
    'get_canonical_string',
    'get_canonical_mac_address',
    'get_canonical_constant',
    'get_canonical_memory',
    'get_canonical_count',
    'get_canonical_date',
    'is_integer',
    'get_regexp_oid_match',
    'sorted_ports'
]


def get_canonical_serial_number(value: Optional[str]) -> Optional[str]:
    """
    Return a clean serial number string.
    
    Args:
        value: Raw serial number from SNMP
        
    Returns:
        Cleaned serial number or None
    """
    value = hex2char(value)
    if not value:
        return None
    
    # Remove non-printable characters
    value = re.sub(r'[^\x20-\x7E]', '', value)
    
    # Remove leading/trailing whitespace
    value = value.strip()
    
    # Remove multiple consecutive dots
    value = re.sub(r'\.{2,}', '', value)
    
    return value if value else None


def get_canonical_string(value: Optional[str]) -> Optional[str]:
    """
    Return a clean generic string.
    
    Args:
        value: Raw string from SNMP
        
    Returns:
        Cleaned string or None
    """
    value = hex2char(value)
    if value is None:
        return None
    
    # Unquote string
    value = re.sub(r'^\\?["\']', '', value)
    value = re.sub(r'\\?["\']$', '', value)
    
    # Ensure UTF-8
    value = get_utf8_string(value)
    if value is None:
        return None
    
    # Reduce linefeeds (control characters followed by newline)
    value = re.sub(r'[\x00-\x1F]+\n', '\n', value)
    
    # Decode to UTF-8
    if isinstance(value, bytes):
        try:
            value = value.decode('utf-8', errors='ignore')
        except Exception:
            pass
    
    # Truncate after first invalid character (keep newlines)
    match = re.search(r'[^\x20-\x7E\n]', value)
    if match:
        value = value[:match.start()]
    
    # Cleanup trailing newlines
    value = value.rstrip('\n')
    
    return value if value else None


def get_canonical_mac_address(value: Optional[str]) -> Optional[str]:
    """
    Return a clean MAC address string.
    
    Args:
        value: Raw MAC address from SNMP (can be binary, hex, or colon-separated)
        
    Returns:
        Canonical MAC address (lowercase with colons) or None
    """
    if not value:
        return None
    
    bytes_list = []
    
    # If packed binary value (length 6 or all ASCII), convert to hex
    if len(value) == 6 or all(32 <= ord(c) <= 127 for c in value if isinstance(c, str)):
        if isinstance(value, str):
            value = ''.join(f'{ord(c):02x}' for c in value)
        else:
            value = value.hex()
    
    # Check if it's a hex value
    match = re.match(r'^(?:0x)?([0-9A-F]+)$', value, re.I)
    if match:
        hex_str = match.group(1)
        # Split into 2-character chunks
        bytes_list = [hex_str[i:i+2] for i in range(0, len(hex_str), 2)]
    else:
        # Split by colons
        bytes_list = value.split(':')
        # Return None if bytes are not hex
        if not all(re.match(r'^[0-9A-F]{1,2}$', b, re.I) for b in bytes_list):
            return None
    
    # Process based on number of bytes
    if len(bytes_list) == 6:
        # It's a MAC address
        pass
    elif len(bytes_list) == 8:
        # Check if it's a WWN
        if (bytes_list[0] == '10' and re.match(r'^0+$', bytes_list[1])) or \
           bytes_list[0].startswith('2'):
            # It's a WWN, keep as is
            pass
        else:
            # Take last 6 bytes for MAC
            bytes_list = bytes_list[-6:]
    elif len(bytes_list) < 6:
        # Make a WWN: prepend "10" and zeros as necessary
        while len(bytes_list) < 7:
            bytes_list.insert(0, '00')
        bytes_list.insert(0, '10')
    elif len(bytes_list) > 6:
        # Make a MAC: take 6 bytes from the right
        bytes_list = bytes_list[-6:]
    
    # Format as MAC address
    result = ':'.join(f'{int(b, 16):02x}' for b in bytes_list)
    
    # Don't return all-zeros MAC
    if result == '00:00:00:00:00:00':
        return None
    
    return result.lower()


def is_integer(value: Any) -> bool:
    """
    Return True if value is an integer.
    
    Args:
        value: Value to check
        
    Returns:
        True if integer, False otherwise
    """
    if isinstance(value, int):
        return True
    
    if isinstance(value, str):
        return bool(re.match(r'^[+-]?\d+$', value))
    
    return False


def get_canonical_memory(value: Any) -> Optional[int]:
    """
    Return memory size in MB.
    
    Args:
        value: Raw memory value (can include units)
        
    Returns:
        Memory in MB or None
    """
    if not value:
        return None
    
    value_str = str(value)
    
    # Don't analyze negative values
    if value_str.startswith('-'):
        return None
    
    # Check for KB units
    match = re.match(r'^(\d+)\s*(KBytes|kB)$', value_str)
    if match:
        return int(match.group(1)) // 1024
    
    # Assume bytes, convert to MB
    try:
        return int(value) // (1024 * 1024)
    except (ValueError, TypeError):
        return None


def get_canonical_count(value: Any) -> Optional[int]:
    """
    Return count as integer if valid.
    
    Args:
        value: Value to check
        
    Returns:
        Integer value or None
    """
    if is_integer(value):
        return int(value)
    return None


def get_canonical_constant(value: Any) -> Optional[int]:
    """
    Return a clean integer constant value.
    
    Args:
        value: Raw constant value (can be like "someValue(5)")
        
    Returns:
        Integer value or None
    """
    if is_integer(value):
        return int(value)
    
    # Extract number from parentheses like "someValue(5)"
    if isinstance(value, str):
        match = re.search(r'\((\d+)\)$', value)
        if match:
            return int(match.group(1))
    
    return None


def get_regexp_oid_match(match: str) -> Optional[Pattern]:
    """
    Return compiled regexp to match given OID.
    
    Args:
        match: OID string (e.g., "1.3.6.1.2.1")
        
    Returns:
        Compiled regex pattern or None
    """
    if not match or not re.match(r'^[0-9.]+$', match):
        return None if match else None
    
    # Escape dots for regexp
    escaped = match.replace('.', '\\.')
    
    return re.compile(f'^{escaped}')


# Month name to number mapping
MONTHS = {
    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4,
    'May': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8,
    'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
}


def get_canonical_date(value: Optional[str]) -> Optional[str]:
    """
    Return date in YYYY-MM-DD format if possible.
    
    Args:
        value: Raw date string in various formats
        
    Returns:
        Date in YYYY-MM-DD format or None
    """
    if empty(value):
        return None
    
    value = str(value).strip()
    
    # Match 'D M d H:i:s Y' (e.g., "Mon Jan 1 12:34:56 2024")
    match = re.match(
        r'^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})\s+\d{2}:\d{2}:\d{2}\s+.*([1-9]\d{3})$',
        value
    )
    if match:
        month_name, day, year = match.groups()
        return f"{int(year):04d}-{MONTHS[month_name]:02d}-{int(day):02d}"
    
    # Match 'D M d, Y H:i:s' (e.g., "Wed Aug 01, 2012 05:50:43PM")
    match = re.match(
        r'^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}),\s+([1-9]\d{3})\s+',
        value
    )
    if match:
        month_name, day, year = match.groups()
        return f"{int(year):04d}-{MONTHS[month_name]:02d}-{int(day):02d}"
    
    # Match 'Y-m-d\TH:i:sZ' (ISO format)
    match = re.match(r'^([1-9]\d{3})-(\d{1,2})-(\d{1,2})', value)
    if match:
        year, month, day = match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    
    # Match 'd/m/Y H:i:s'
    match = re.match(r'^(\d{1,2})/(\d{1,2})/([1-9]\d{3})', value)
    if match:
        day, month, year = match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    
    # Match 'm/d/Y' (US format)
    match = re.match(r'^(\d{1,2})/(\d{1,2})/([1-9]\d{3})', value)
    if match:
        month, day, year = match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    
    # Match 'd.m.Y' (European format)
    match = re.match(r'^(\d{1,2})\.(\d{1,2})\.([1-9]\d{3})', value)
    if match:
        day, month, year = match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    
    # Match 'Ymd' (compact format)
    match = re.match(r'^([1-9]\d{3})(\d{2})(\d{2})$', value)
    if match:
        year, month, day = match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    
    return None


def sorted_ports(ports: Optional[Dict]) -> List:
    """
    Return sorted list of port numbers/IDs.
    
    Args:
        ports: Dictionary of ports
        
    Returns:
        List of port IDs sorted numerically
    """
    if not isinstance(ports, dict):
        return []
    
    return sorted(ports.keys(), key=_numify_port)


def _numify_port(num: Any) -> float:
    """
    Convert port identifier to a sortable number.
    
    Args:
        num: Port identifier (can be like "1", "1.2", "1.2.3")
        
    Returns:
        Float representation for sorting
    """
    num_str = str(num)
    
    # Simple integer
    if re.match(r'^\d+$', num_str):
        return float(num_str)
    
    # Not a valid format
    if not re.match(r'^[0-9.]+$', num_str):
        return 0.0
    
    # Digits separated by dots (e.g., "1.2.3")
    parts = num_str.split('.')
    if not parts:
        return 0.0
    
    # First part is the main number
    main_num = float(parts[0])
    
    # Remaining parts become fractional components
    if len(parts) > 1:
        decimal_parts = ''.join(f'{int(p):03d}' for p in parts[1:])
        return float(f"{main_num}.{decimal_parts}")
    
    return main_num


if __name__ == '__main__':
    print("GLPI Agent Tools SNMP Module")
    print("\nTesting SNMP functions:")
    print(f"  get_canonical_mac_address('aabbccddeeff'): {get_canonical_mac_address('aabbccddeeff')}")
    print(f"  is_integer('123'): {is_integer('123')}")
    print(f"  is_integer('abc'): {is_integer('abc')}")
    print(f"  get_canonical_memory('1024 KBytes'): {get_canonical_memory('1024 KBytes')}")
