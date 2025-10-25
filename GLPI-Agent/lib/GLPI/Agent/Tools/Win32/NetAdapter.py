#!/usr/bin/env python3
"""
GLPI Agent Win32 NetAdapter - Python Implementation

Windows network adapter information handler via WMI.
"""

import re
from typing import List, Dict, Optional, Any

try:
    from GLPI.Agent.Tools.Network import (
        ip_address_pattern, get_subnet_address, get_subnet_address_ipv6,
        get_network_mask_ipv6
    )
except ImportError:
    # Mock for standalone usage
    ip_address_pattern = r'\d{1,3}(?:\.\d{1,3}){3}'
    
    def get_subnet_address(ip, mask):
        return None
    
    def get_subnet_address_ipv6(ip, mask):
        return None
    
    def get_network_mask_ipv6(prefix):
        return None


__all__ = ['NetAdapter']


# IANA Interface types mapping
INTERFACE_TYPES = {
    6: 'ethernet',
    7: 'ethernet',
    56: 'fiberchannel',
    62: 'ethernet',
    71: 'wifi',
    117: 'ethernet',
    169: 'ethernet'
}


class NetAdapter:
    """
    Windows Network Adapter handler.
    
    Processes network adapter information from WMI data.
    """
    
    def __init__(self, WMI: Dict, configurations: List[Dict]):
        """
        Initialize network adapter from WMI data.
        
        Args:
            WMI: WMI network adapter object data
            configurations: List of network adapter configurations
        """
        if not WMI or not configurations:
            raise ValueError("WMI and configurations are required")
        
        # Copy WMI data
        for key, value in WMI.items():
            setattr(self, key, value)
        
        # Get configuration for this adapter
        self._config = configurations[self._get_object_index()]
        if not self._config:
            raise ValueError("No configuration found for adapter")
        
        if not self._get_pnpdevice_id():
            raise ValueError("No PNP Device ID found")
    
    def _get_object_index(self) -> int:
        """Get the index of this adapter in the configurations list."""
        # In Perl, Index is a property from WMI
        return getattr(self, 'Index', 0)
    
    def _get_pnpdevice_id(self) -> Optional[str]:
        """Get PNP Device ID."""
        return getattr(self, 'PNPDeviceID', None)
    
    def _get_description(self) -> Optional[str]:
        """Get adapter description."""
        return getattr(self, 'Description', None) or getattr(self, 'Name', None)
    
    def _get_pciid(self) -> Optional[str]:
        """Extract PCI ID from PNP Device ID."""
        pnp_id = self._get_pnpdevice_id()
        if not pnp_id:
            return None
        
        # Extract PCI ID from PNPDeviceID
        # Format: PCI\VEN_XXXX&DEV_YYYY&...
        match = re.search(r'VEN_([0-9A-F]{4})&DEV_([0-9A-F]{4})', pnp_id, re.I)
        if match:
            return f"{match.group(1).lower()}:{match.group(2).lower()}"
        
        return None
    
    def _get_guid(self) -> Optional[str]:
        """Get adapter GUID."""
        return getattr(self, 'GUID', None) or getattr(self, 'SettingID', None)
    
    def _is_virtual(self) -> bool:
        """Check if adapter is virtual."""
        # Check various indicators for virtual adapters
        pnp_id = self._get_pnpdevice_id() or ''
        description = self._get_description() or ''
        
        virtual_indicators = [
            'VirtualBox', 'VMware', 'Hyper-V', 'vEthernet',
            'TAP-Win', 'VPN', 'Loopback', 'Pseudo'
        ]
        
        for indicator in virtual_indicators:
            if indicator.lower() in pnp_id.lower() or indicator.lower() in description.lower():
                return True
        
        return False
    
    def has_addresses(self) -> bool:
        """Check if adapter has IP addresses."""
        addresses = self._config.get('addresses', [])
        return bool(addresses)
    
    def get_interfaces(self) -> Optional[List[Dict]]:
        """
        Get interface information.
        
        Returns:
            List of interface dictionaries or None
        """
        if self.has_addresses():
            return self.get_interfaces_with_addresses()
        
        # Return base interface for VPN or if MAC address exists
        mac = self._config.get('MACADDR')
        desc = self._get_description() or ''
        if mac or 'vpn' in desc.lower():
            return [self.get_base_interface()]
        
        return None
    
    def get_base_interface(self) -> Dict:
        """
        Get base interface information.
        
        Returns:
            Dictionary containing base interface data
        """
        interface = {
            'PNPDEVICEID': self._get_pnpdevice_id(),
            'MACADDR': self._config.get('MACADDR'),
            'DESCRIPTION': self._get_description(),
            'STATUS': self._config.get('STATUS'),
            'MTU': self._config.get('MTU'),
            'dns': self._config.get('dns'),
            'VIRTUALDEV': self._is_virtual()
        }
        
        # Add optional fields
        pciid = self._get_pciid()
        if pciid:
            interface['PCIID'] = pciid
        
        guid = self._get_guid()
        if guid:
            interface['GUID'] = guid
        
        dns_domain = self._config.get('DNSDomain')
        if dns_domain:
            interface['DNSDomain'] = dns_domain
        
        speed = getattr(self, 'Speed', None)
        if speed:
            try:
                interface['SPEED'] = int(speed) // 1_000_000
            except (ValueError, TypeError):
                pass
        
        # Set interface type based on IANA standards
        interface_type = getattr(self, 'InterfaceType', None)
        if interface_type and interface_type in INTERFACE_TYPES:
            interface['TYPE'] = INTERFACE_TYPES[interface_type]
        
        return interface
    
    def get_interfaces_with_addresses(self) -> List[Dict]:
        """
        Get interfaces with IP addresses.
        
        Returns:
            List of interface dictionaries with addresses
        """
        interfaces = []
        addresses = self._config.get('addresses', [])
        
        for address_pair in addresses:
            interface = self.get_base_interface()
            
            address = address_pair[0]
            prefix_or_mask = address_pair[1]
            
            # Check if IPv4 or IPv6
            if re.match(ip_address_pattern, address):
                # IPv4
                interface['IPADDRESS'] = address
                interface['IPMASK'] = prefix_or_mask
                interface['IPSUBNET'] = get_subnet_address(
                    interface['IPADDRESS'],
                    interface['IPMASK']
                )
                interface['IPDHCP'] = self._config.get('IPDHCP')
                interface['IPGATEWAY'] = self._config.get('IPGATEWAY')
            else:
                # IPv6
                interface['IPADDRESS6'] = address
                # Remove any win32 scope ID from local IPv6 address
                interface['IPADDRESS6'] = re.sub(r'%\d+$', '', interface['IPADDRESS6'])
                interface['IPMASK6'] = get_network_mask_ipv6(prefix_or_mask)
                interface['IPSUBNET6'] = get_subnet_address_ipv6(
                    interface['IPADDRESS6'],
                    interface['IPMASK6']
                ) if interface.get('IPMASK6') else None
            
            interfaces.append(interface)
        
        return interfaces


if __name__ == '__main__':
    print("GLPI Agent Win32 NetAdapter Module")
    print("Windows network adapter information handler")
