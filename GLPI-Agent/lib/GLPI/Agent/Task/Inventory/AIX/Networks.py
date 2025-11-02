#!/usr/bin/env python3
"""
GLPI Agent Task Inventory AIX Networks - Python Implementation
"""

import re
from typing import Dict, Any, List

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines, get_first_line
from GLPI.Agent.Tools.Unix import get_routing_table
from GLPI.Agent.Tools.Network import (
    is_same_network, 
    get_subnet_address,
    IP_ADDRESS_PATTERN,
    ALT_MAC_ADDRESS_PATTERN,
    alt2canonical
)


class Networks(InventoryModule):
    """AIX Networks inventory module."""
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "network"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('lscfg')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        routes = get_routing_table(command='netstat -nr', logger=logger)
        default = routes.get('0.0.0.0') or routes.get('default')
        
        interfaces = Networks._get_interfaces(logger=logger)
        for interface in interfaces:
            # if the default gateway address and the interface address belongs to
            # the same network, that's the gateway for this network
            if default and is_same_network(
                default, 
                interface.get('IPADDRESS'), 
                interface.get('IPMASK')
            ):
                interface['IPGATEWAY'] = default
            
            if inventory:
                inventory.add_entry(
                    section='NETWORKS',
                    entry=interface
                )
        
        if inventory and default:
            inventory.set_hardware({
                'DEFAULTGATEWAY': default
            })
    
    @staticmethod
    def _get_interfaces(**params) -> List[Dict[str, Any]]:
        """Get network interfaces information."""
        logger = params.get('logger')
        
        # get a list of interfaces from ifconfig
        ifconfig_line = get_first_line(command='ifconfig -l')
        interfaces = []
        if ifconfig_line:
            for iface in ifconfig_line.split():
                interfaces.append({'DESCRIPTION': iface})
        
        # complete with hardware addresses, extracted from lscfg
        addresses = Networks._parse_lscfg(
            command='lscfg -v -l ent*',
            logger=logger
        )
        
        for interface in interfaces:
            desc = interface.get('DESCRIPTION')
            if desc and desc in addresses:
                interface['TYPE'] = 'ethernet'
                interface['MACADDR'] = addresses[desc]
        
        # complete with network information, extracted from lsattr
        for interface in interfaces:
            desc = interface.get('DESCRIPTION')
            if not desc:
                continue
                
            lines = get_all_lines(
                command=f"lsattr -E -l {desc}",
                logger=logger
            )
            if not lines:
                continue
            
            for line in lines:
                # Match IP address
                match = re.match(rf'^netaddr\s+({IP_ADDRESS_PATTERN})', line, re.VERBOSE)
                if match:
                    interface['IPADDRESS'] = match.group(1)
                
                # Match netmask
                match = re.match(rf'^netmask\s+({IP_ADDRESS_PATTERN})', line, re.VERBOSE)
                if match:
                    interface['IPMASK'] = match.group(1)
                
                # Match status
                match = re.match(r'^state\s+(\w+)', line, re.VERBOSE)
                if match:
                    interface['STATUS'] = match.group(1)
        
        for interface in interfaces:
            ip_address = interface.get('IPADDRESS')
            ip_mask = interface.get('IPMASK')
            
            if ip_address and ip_mask:
                interface['IPSUBNET'] = get_subnet_address(ip_address, ip_mask)
            
            if not ip_address:
                interface['STATUS'] = 'Down'
            
            interface['IPDHCP'] = 'No'
        
        return interfaces
    
    @staticmethod
    def _parse_lscfg(**params) -> Dict[str, str]:
        """Parse lscfg output to extract MAC addresses."""
        lines = get_all_lines(**params)
        if not lines:
            return {}
        
        addresses = {}
        current_interface = None
        
        for line in lines:
            # Match interface name
            match = re.match(r'^\s+ent(\d+)\s+\S+\s+', line, re.VERBOSE)
            if match:
                current_interface = f"en{match.group(1)}"
            
            # Match MAC address
            match = re.search(rf'Network Address\.+({ALT_MAC_ADDRESS_PATTERN})', line)
            if match and current_interface:
                addresses[current_interface] = alt2canonical(match.group(1))
        
        return addresses
