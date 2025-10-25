#!/usr/bin/env python3
"""
GLPI Agent Tools Network - Python Implementation

Network-related patterns and functions for IP address and MAC address manipulation.
"""

import re
import socket
import ipaddress
from typing import List, Optional, Union

__all__ = [
    'mac_address_pattern',
    'ib_mac_address_pattern',
    'any_mac_address_pattern',
    'ip_address_pattern',
    'alt_mac_address_pattern',
    'hex_ip_address_pattern',
    'network_pattern',
    'get_subnet_address',
    'get_subnet_address_ipv6',
    'get_network_mask',
    'get_network_mask_ipv6',
    'is_same_network',
    'is_same_network_ipv6',
    'hex2canonical',
    'alt2canonical',
    'resolve',
    'compile_address',
    'is_part_of'
]


# Network address patterns
dec_byte = r'[0-9]{1,3}'
hex_byte = r'[0-9A-F]{1,2}'
padded_hex_byte = r'[0-9A-F]{2}'

# MAC address pattern (aa:bb:cc:dd:ee:ff)
mac_address_pattern = rf'{hex_byte}:{hex_byte}:{hex_byte}:{hex_byte}:{hex_byte}:{hex_byte}'

# InfiniBand MAC address pattern (20 bytes)
ib_mac_address_pattern = rf'{hex_byte}:{hex_byte}:{hex_byte}:{hex_byte}:{hex_byte}:{hex_byte}:' \
                          rf'{hex_byte}:{hex_byte}:{hex_byte}:{hex_byte}:{hex_byte}:{hex_byte}:' \
                          rf'{hex_byte}:{hex_byte}:{hex_byte}:{hex_byte}:{hex_byte}:{hex_byte}:' \
                          rf'{hex_byte}:{hex_byte}'

# Any MAC address pattern (standard or InfiniBand)
any_mac_address_pattern = rf'(?:{ib_mac_address_pattern}|{mac_address_pattern})'

# IP address pattern (xxx.xxx.xxx.xxx)
ip_address_pattern = rf'{dec_byte}\.{dec_byte}\.{dec_byte}\.{dec_byte}'

# Alternative MAC address pattern (aabbccddeeff)
alt_mac_address_pattern = rf'{padded_hex_byte}{padded_hex_byte}{padded_hex_byte}' \
                           rf'{padded_hex_byte}{padded_hex_byte}{padded_hex_byte}'

# Hexadecimal IP address pattern (aabbccdd)
hex_ip_address_pattern = rf'{padded_hex_byte}{padded_hex_byte}{padded_hex_byte}{padded_hex_byte}'

# Network pattern with CIDR notation
network_pattern = rf'{dec_byte}(?:\.{dec_byte}(?:\.{dec_byte}(?:\.{dec_byte})?)?)?/\d{{1,2}}'


def get_subnet_address(address: str, mask: str) -> Optional[str]:
    """
    Returns the subnet address for IPv4.
    
    Args:
        address: IP address string
        mask: Netmask string
        
    Returns:
        Subnet address string or None
    """
    if not address or not mask:
        return None
    
    try:
        addr = ipaddress.IPv4Address(address)
        netmask = ipaddress.IPv4Address(mask)
        subnet = ipaddress.IPv4Address(int(addr) & int(netmask))
        return str(subnet)
    except (ValueError, ipaddress.AddressValueError):
        return None


def get_subnet_address_ipv6(address: str, mask: str) -> Optional[str]:
    """
    Returns the subnet address for IPv6.
    
    Args:
        address: IPv6 address string
        mask: IPv6 netmask string
        
    Returns:
        Subnet address string or None
    """
    if not address or not mask:
        return None
    
    try:
        addr = ipaddress.IPv6Address(address)
        netmask = ipaddress.IPv6Address(mask)
        subnet = ipaddress.IPv6Address(int(addr) & int(netmask))
        return str(subnet.compressed)
    except (ValueError, ipaddress.AddressValueError):
        return None


def is_same_network(address1: str, address2: str, mask: str) -> Optional[bool]:
    """
    Returns True if both addresses belong to the same network, for IPv4.
    
    Args:
        address1: First IP address
        address2: Second IP address
        mask: Netmask
        
    Returns:
        True if same network, False otherwise, None on error
    """
    if not address1 or not address2 or not mask:
        return None
    
    try:
        addr1 = ipaddress.IPv4Address(address1)
        addr2 = ipaddress.IPv4Address(address2)
        netmask = ipaddress.IPv4Address(mask)
        
        return (int(addr1) & int(netmask)) == (int(addr2) & int(netmask))
    except (ValueError, ipaddress.AddressValueError):
        return None


def is_same_network_ipv6(address1: str, address2: str, mask: str) -> Optional[bool]:
    """
    Returns True if both addresses belong to the same network, for IPv6.
    
    Args:
        address1: First IPv6 address
        address2: Second IPv6 address
        mask: IPv6 netmask
        
    Returns:
        True if same network, False otherwise, None on error
    """
    if not address1 or not address2 or not mask:
        return None
    
    try:
        addr1 = ipaddress.IPv6Address(address1)
        addr2 = ipaddress.IPv6Address(address2)
        netmask = ipaddress.IPv6Address(mask)
        
        return (int(addr1) & int(netmask)) == (int(addr2) & int(netmask))
    except (ValueError, ipaddress.AddressValueError):
        return None


def hex2canonical(address: str) -> Optional[str]:
    """
    Convert an IP address from hexadecimal to canonical form.
    
    Args:
        address: Hexadecimal IP address (e.g., "C0A80001" or "0xC0A80001")
        
    Returns:
        Canonical IP address (e.g., "192.168.0.1") or None
    """
    if not address:
        return None
    
    # Remove 0x prefix if present
    addr_clean = address.replace('0x', '').replace('0X', '')
    
    # Match 4 hex bytes
    match = re.match(r'^([0-9A-Fa-f]{2})([0-9A-Fa-f]{2})([0-9A-Fa-f]{2})([0-9A-Fa-f]{2})$', addr_clean)
    if not match:
        return None
    
    bytes_list = [int(b, 16) for b in match.groups()]
    return '.'.join(map(str, bytes_list))


def alt2canonical(address: str) -> Optional[str]:
    """
    Convert a MAC address from alternative to canonical form.
    
    Args:
        address: Alternative MAC address (e.g., "aabbccddeeff" or "aa-bb-cc-dd-ee-ff")
        
    Returns:
        Canonical MAC address (e.g., "aa:bb:cc:dd:ee:ff") or None
    """
    if not address:
        return None
    
    # Remove 0x prefix if present and any separators
    addr_clean = address.replace('0x', '').replace('0X', '')
    
    # Match 6 hex bytes with optional separators
    match = re.match(
        r'^([0-9A-Fa-f]{2})[ :-]?([0-9A-Fa-f]{2})[ :-]?([0-9A-Fa-f]{2})[ :-]?'
        r'([0-9A-Fa-f]{2})[ :-]?([0-9A-Fa-f]{2})[ :-]?([0-9A-Fa-f]{2})$',
        addr_clean
    )
    
    if not match:
        return None
    
    return ':'.join(b.lower() for b in match.groups())


def get_network_mask(prefix: int) -> Optional[str]:
    """
    Returns the network mask for IPv4 from a prefix length.
    
    Args:
        prefix: Prefix length (0-32)
        
    Returns:
        Netmask string or None
    """
    if prefix is None or prefix < 0 or prefix > 32:
        return None
    
    try:
        network = ipaddress.IPv4Network(f'0.0.0.0/{prefix}', strict=False)
        return str(network.netmask)
    except (ValueError, ipaddress.AddressValueError):
        return None


def get_network_mask_ipv6(prefix: int) -> Optional[str]:
    """
    Returns the network mask for IPv6 from a prefix length.
    
    Args:
        prefix: Prefix length (0-128)
        
    Returns:
        IPv6 netmask string or None
    """
    if prefix is None or prefix < 0 or prefix > 128:
        return None
    
    try:
        network = ipaddress.IPv6Network(f'::/{prefix}', strict=False)
        return str(network.netmask.compressed)
    except (ValueError, ipaddress.AddressValueError):
        return None


def resolve(name: str, logger=None) -> List[Union[ipaddress.IPv4Address, ipaddress.IPv6Address]]:
    """
    Returns a list of addresses for the given host name.
    
    Args:
        name: Hostname to resolve
        logger: Logger object
        
    Returns:
        List of IP address objects
    """
    addresses = []
    errors = []
    
    try:
        # Try to resolve using getaddrinfo (supports both IPv4 and IPv6)
        results = socket.getaddrinfo(name, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        
        for result in results:
            addr_str = result[4][0]
            # Drop the zone index for IPv6, as not all libraries support it
            addr_str = re.sub(r'%.*$', '', addr_str)
            
            try:
                # Try IPv6 first
                addresses.append(ipaddress.IPv6Address(addr_str))
            except ipaddress.AddressValueError:
                try:
                    # Then IPv4
                    addresses.append(ipaddress.IPv4Address(addr_str))
                except ipaddress.AddressValueError:
                    errors.append(f"unable to parse address '{addr_str}' for '{name}'")
    
    except socket.gaierror as e:
        errors.append(f"unable to get address for '{name}': {e}")
    
    if errors and logger:
        for error in errors:
            logger.error(error)
    
    return addresses


def _expand_ipv4_to_ipv6(addresses: List) -> List:
    """
    Expand IPv4 addresses to IPv6-mapped IPv4 addresses.
    
    Args:
        addresses: List of IP address objects
        
    Returns:
        Extended list with IPv6-mapped addresses
    """
    expanded = []
    for addr in addresses:
        if isinstance(addr, ipaddress.IPv4Address):
            # Add IPv6-mapped IPv4 address
            ipv6_addr = ipaddress.IPv6Address('::ffff:' + str(addr))
            expanded.append(ipv6_addr)
            
            # Also include shorten ipv6 loopback address if needed
            if str(addr) == '127.0.0.1':
                expanded.append(ipaddress.IPv6Address('::1'))
    
    return addresses + expanded


def compile_address(string: str, logger=None) -> List:
    """
    Returns a list of addresses for the given IP address or host name.
    
    Args:
        string: IP address or hostname
        logger: Logger object
        
    Returns:
        List of IP address objects
    """
    if not string:
        return []
    
    # Check if it's already an IP address
    try:
        # Try as IPv4/IPv6 network or address
        if '/' in string:
            network = ipaddress.ip_network(string, strict=False)
            return _expand_ipv4_to_ipv6([network.network_address])
        else:
            addr = ipaddress.ip_address(string)
            return _expand_ipv4_to_ipv6([addr])
    except ValueError:
        pass
    
    # Otherwise resolve as hostname
    return _expand_ipv4_to_ipv6(resolve(string, logger))


def is_part_of(string: str, ranges: List, logger=None) -> bool:
    """
    Returns True if the given address is part of any address/range from the list.
    
    Args:
        string: IP address string
        ranges: List of IP network objects
        logger: Logger object
        
    Returns:
        True if address is part of any range, False otherwise
    """
    if not string or not ranges:
        return False
    
    try:
        address = ipaddress.ip_address(string)
    except ValueError as e:
        if logger:
            logger.error(f"Not well formatted source IP: {string}")
        return False
    
    # Filter ranges to same IP version
    same_version_ranges = [r for r in ranges if isinstance(r, ipaddress.IPv4Network) == isinstance(address, ipaddress.IPv4Address) or 
                           isinstance(r, ipaddress.IPv6Network) == isinstance(address, ipaddress.IPv6Address)]
    
    for ip_range in same_version_ranges:
        try:
            if isinstance(ip_range, (ipaddress.IPv4Network, ipaddress.IPv6Network)):
                if address in ip_range:
                    return True
            elif isinstance(ip_range, (ipaddress.IPv4Address, ipaddress.IPv6Address)):
                if address == ip_range:
                    return True
        except Exception as e:
            if logger:
                logger.debug(f"Server: {e}")
            continue
    
    return False


if __name__ == '__main__':
    print("GLPI Agent Tools Network Module")
    print("\nTesting network functions:")
    print(f"  hex2canonical('C0A80001'): {hex2canonical('C0A80001')}")
    print(f"  alt2canonical('aa-bb-cc-dd-ee-ff'): {alt2canonical('aa-bb-cc-dd-ee-ff')}")
    print(f"  get_network_mask(24): {get_network_mask(24)}")
    print(f"  is_same_network('192.168.1.1', '192.168.1.100', '255.255.255.0'): {is_same_network('192.168.1.1', '192.168.1.100', '255.255.255.0')}")
