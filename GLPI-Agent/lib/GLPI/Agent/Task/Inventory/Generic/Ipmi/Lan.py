#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Ipmi Lan - Python Implementation

OcsInventory agent - IPMI lan channel report

Copyright (c) 2008 Jean Parpaillon <jean.parpaillon@kerlabs.com>

The Intelligent Platform Management Interface (IPMI) specification
defines a set of common interfaces to a computer system which system
administrators can use to monitor system health and manage the
system. The IPMI consists of a main controller called the Baseboard
Management Controller (BMC) and other satellite controllers.

The BMC can be fetched through client like OpenIPMI drivers or
through the network. Though, the BMC hold a proper MAC address.

This module reports the MAC address and, if any, the IP
configuration of the BMC. This is reported as a standard NIC.
"""

import re
from typing import Any, Dict, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import get_all_lines
from GLPI.Agent.Tools.Network import get_subnet_address, ip_address_pattern, mac_address_pattern


class Lan(InventoryModule):
    """IPMI LAN inventory module."""
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "network"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return True
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        interface = Lan._get_ipmitool_interface(logger=logger)
        if not interface:
            return
        
        if inventory:
            inventory.add_entry(
                section='NETWORKS',
                entry=interface
            )
    
    @staticmethod
    def _get_ipmitool_interface(**params) -> Optional[Dict[str, Any]]:
        """Get BMC interface information via ipmitool."""
        lines = get_all_lines(
            command='ipmitool lan print',
            **params
        )
        if not lines:
            return None
        
        interface = {
            'DESCRIPTION': 'bmc',
            'TYPE': 'ethernet',
            'MANAGEMENT': 1,
            'STATUS': 'Down',
        }
        
        for line in lines:
            # IP Address
            match = re.match(rf'^IP Address\s+:\s+({ip_address_pattern()})', line)
            if match:
                ip = match.group(1)
                if ip != '0.0.0.0':
                    interface['IPADDRESS'] = ip
            
            # Default Gateway IP
            match = re.match(rf'^Default Gateway IP\s+:\s+({ip_address_pattern()})', line)
            if match:
                gateway = match.group(1)
                if gateway != '0.0.0.0':
                    interface['IPGATEWAY'] = gateway
            
            # Subnet Mask
            match = re.match(rf'^Subnet Mask\s+:\s+({ip_address_pattern()})', line)
            if match:
                mask = match.group(1)
                if mask != '0.0.0.0':
                    interface['IPMASK'] = mask
            
            # MAC Address
            match = re.match(rf'^MAC Address\s+:\s+({mac_address_pattern()})', line)
            if match:
                interface['MACADDR'] = match.group(1)
        
        if interface.get('IPADDRESS'):
            interface['IPSUBNET'] = get_subnet_address(
                interface['IPADDRESS'],
                interface.get('IPMASK')
            )
            interface['STATUS'] = 'Up'
        
        return interface
