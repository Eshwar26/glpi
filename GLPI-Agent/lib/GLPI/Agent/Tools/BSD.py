#!/usr/bin/env python3
"""
GLPI Agent BSD Tools - Python Implementation

This module provides BSD-specific generic functions for the GLPI Agent.
"""

from typing import Dict, List, Optional, Any
import re

# Import the main Tools module functions
try:
    from GLPI.Agent.Tools import get_all_lines, any_func
    from GLPI.Agent.Tools.Network import (
        hex2canonical, get_subnet_address, get_network_mask_ipv6,
        get_subnet_address_ipv6, mac_address_pattern, ip_address_pattern
    )
except ImportError:
    import sys
    sys.path.insert(0, '../../')
    from Tools import get_all_lines, any_func
    # Mock network functions for standalone usage
    mac_address_pattern = r'[0-9a-f]{2}(?::[0-9a-f]{2}){5}'
    ip_address_pattern = r'\d+\.\d+\.\d+\.\d+'
    
    def hex2canonical(value):
        """Convert hex to canonical format."""
        return value
    
    def get_subnet_address(address, mask):
        """Get subnet address."""
        return address
    
    def get_network_mask_ipv6(prefix):
        """Get IPv6 network mask."""
        return prefix
    
    def get_subnet_address_ipv6(address, mask):
        """Get IPv6 subnet address."""
        return address


__all__ = [
    'get_interfaces_from_ifconfig'
]


def get_interfaces_from_ifconfig(**params) -> List[Dict[str, Any]]:
    """
    Get network interfaces from ifconfig command output.
    
    Args:
        **params: Optional parameters including:
            - command: Command to execute (default: '/sbin/ifconfig -a')
            - file: File to read from instead of running command
            - logger: Logger object
            
    Returns:
        List of dictionaries containing interface information
        
    Example output:
        [
            {
                'DESCRIPTION': 'eth0',
                'STATUS': 'Up',
                'MTU': 1500,
                'MACADDR': '00:11:22:33:44:55',
                'IPADDRESS': '192.168.1.10',
                'IPMASK': '255.255.255.0',
                'IPSUBNET': '192.168.1.0',
                'TYPE': 'ethernet'
            },
            ...
        ]
    """
    # Set default command if not specified
    if 'command' not in params:
        params['command'] = '/sbin/ifconfig -a'
    
    lines = get_all_lines(**params)
    if not lines:
        return []
    
    interfaces = []  # Global list of interfaces
    addresses = []   # Per-interface list of addresses
    interface = None  # Current interface
    
    # Interface types mapping
    types = {
        'Ethernet': 'ethernet',
        'IEEE': 'wifi'
    }
    
    for line in lines:
        # Match interface header
        match = re.match(r'^(\S+): flags=\d+<([^>]+)> (?:metric \d+ )?mtu (\d+)', line)
        if match:
            # Save previous interface
            if addresses:
                interfaces.extend(addresses)
                addresses = []
            elif interface:
                interfaces.append(interface)
            
            name, flags, mtu = match.groups()
            
            # Determine status from flags
            flags_list = flags.split(',')
            status = 'Up' if any_func(lambda f: f == 'UP', flags_list) else 'Down'
            
            interface = {
                'DESCRIPTION': name,
                'STATUS': status,
                'MTU': int(mtu)
            }
            continue
        
        if not interface:
            continue
        
        # Match MAC address
        mac_match = re.search(rf'(?:address:|ether|lladdr) ({mac_address_pattern})', line)
        if mac_match:
            interface['MACADDR'] = mac_match.group(1)
            continue
        
        # Match WiFi information
        wifi_match = re.search(
            r'ssid\s+(\S+)\s+channel\s+\d+\s+\(\d+\s+MHz\s+(\S+)[^)]*\)\s+bssid\s+(' + 
            mac_address_pattern + r')', line, re.VERBOSE
        )
        if wifi_match:
            ssid, version, bssid = wifi_match.groups()
            for address in addresses:
                address['WIFI_SSID'] = ssid
                address['WIFI_VERSION'] = '802.' + version
                address['WIFI_BSSID'] = bssid
            continue
        
        # Match IPv4 address
        ipv4_match = re.match(
            rf'inet ({ip_address_pattern}) (?:--> {ip_address_pattern} )?'
            r'netmask 0x([0-9a-fA-F]{8})', line
        )
        if ipv4_match:
            address = ipv4_match.group(1)
            mask = hex2canonical(ipv4_match.group(2))
            subnet = get_subnet_address(address, mask)
            
            addresses.append({
                'IPADDRESS': address,
                'IPMASK': mask,
                'IPSUBNET': subnet,
                'STATUS': interface['STATUS'],
                'DESCRIPTION': interface['DESCRIPTION'],
                'MACADDR': interface.get('MACADDR'),
                'MTU': interface['MTU']
            })
            continue
        
        # Match IPv6 address
        ipv6_match = re.match(r'inet6 ([\w:]+)\S* prefixlen (\d+)', line)
        if ipv6_match:
            address = ipv6_match.group(1)
            prefix = int(ipv6_match.group(2))
            mask = get_network_mask_ipv6(prefix)
            subnet = get_subnet_address_ipv6(address, mask)
            
            addresses.append({
                'IPADDRESS6': address,
                'IPMASK6': mask,
                'IPSUBNET6': subnet,
                'STATUS': interface['STATUS'],
                'DESCRIPTION': interface['DESCRIPTION'],
                'MACADDR': interface.get('MACADDR'),
                'MTU': interface['MTU']
            })
            continue
        
        # Match media type
        media_match = re.search(r'media:\s+(\S+)', line)
        if media_match:
            media_type = media_match.group(1)
            if media_type in types:
                interface['TYPE'] = types[media_type]
                for addr in addresses:
                    addr['TYPE'] = types[media_type]
    
    # Don't forget last interface
    if addresses:
        interfaces.extend(addresses)
    elif interface:
        interfaces.append(interface)
    
    return interfaces


if __name__ == '__main__':
    # Basic testing
    print("GLPI Agent BSD Tools")
    print("Available functions:")
    for func in __all__:
        print(f"  - {func}")
