#!/usr/bin/env python3
"""
GLPI Agent Task Inventory BSD Networks - Python Implementation
"""

import re
from typing import Any, List, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run
from GLPI.Agent.Tools.Network import is_same_network, get_subnet_address
from GLPI.Agent.Tools.Unix import get_routing_table
from GLPI.Agent.Tools.BSD import get_interfaces_from_ifconfig, get_ip_dhcp


class Networks(InventoryModule):
    """BSD Networks inventory module."""
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "network"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('ifconfig')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        routes = get_routing_table(logger=logger)
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
        
        interfaces = get_interfaces_from_ifconfig(logger=logger)
        
        for interface in interfaces:
            ip_address = interface.get('IPADDRESS')
            ip_mask = interface.get('IPMASK')
            
            if ip_address and ip_mask:
                interface['IPSUBNET'] = get_subnet_address(ip_address, ip_mask)
            
            description = interface.get('DESCRIPTION', '')
            interface['IPDHCP'] = get_ip_dhcp(logger, description)
            
            # Check for virtual devices
            if re.match(r'^(lo|vboxnet|vmnet|vtnet|sit|tun|pflog|pfsync|enc|strip|plip|sl|ppp|faith)', description):
                interface['VIRTUALDEV'] = 1
                
                if re.match(r'^lo', description):
                    interface['TYPE'] = 'loopback'
                
                if re.match(r'^ppp', description):
                    interface['TYPE'] = 'dialup'
            else:
                interface['VIRTUALDEV'] = 0
        
        return interfaces
