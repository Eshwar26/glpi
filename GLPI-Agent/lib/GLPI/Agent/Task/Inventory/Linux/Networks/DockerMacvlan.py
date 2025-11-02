#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux Networks DockerMacvlan - Python Implementation
"""

import json
import re
from typing import Any, List, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines
from GLPI.Agent.Tools.Network import get_network_mask, get_network_mask_ipv6, ip_address_pattern


class DockerMacvlan(InventoryModule):
    """Docker macvlan network interface detection module."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('docker')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        networks = DockerMacvlan._get_macvlan_networks(logger=logger)
        if not networks:
            return
        
        for network in networks:
            interfaces = DockerMacvlan._get_interfaces(
                logger=logger,
                networkId=network.strip()
            )
            for interface in interfaces:
                if inventory:
                    inventory.add_entry(
                        section='NETWORKS',
                        entry=interface
                    )
    
    @staticmethod
    def _get_macvlan_networks(**params) -> List[str]:
        """Get macvlan network IDs from Docker."""
        if 'command' not in params:
            params['command'] = 'docker network ls --filter driver=macvlan -q'
        
        return get_all_lines(**params) or []
    
    @staticmethod
    def _get_interfaces(**params) -> List[Dict[str, Any]]:
        """Get network interfaces from Docker network."""
        network_id = params.get('networkId')
        if not network_id:
            return []
        
        lines = get_all_lines(
            command=f'docker network inspect {network_id}',
            **params
        )
        if not lines:
            return []
        
        interfaces = []
        
        # Join all lines for JSON parsing
        lines_str = ''.join(lines) if isinstance(lines, list) else lines
        
        try:
            data = json.loads(lines_str)
        except json.JSONDecodeError:
            return []
        
        if not isinstance(data, list):
            return []
        
        for record in data:
            containers = record.get('Containers', {})
            for k, container in containers.items():
                interface = {
                    'DESCRIPTION': f"{record.get('Name', '')}@{container.get('Name', '')}",
                    'MACADDR': container.get('MacAddress', ''),
                    'STATUS': 'Up',
                    'TYPE': 'ethernet',
                    'VIRTUALDEV': 1
                }
                
                ipv4_address = container.get('IPv4Address', '')
                ipv4_match = re.match(rf'^({ip_address_pattern})/(\d+)$', ipv4_address)
                if ipv4_match:
                    interface['IPADDRESS'] = ipv4_match.group(1)
                    interface['IPMASK'] = get_network_mask(int(ipv4_match.group(2)))
                
                ipv6_address = container.get('IPv6Address', '')
                ipv6_match = re.match(r'^(\S+)/(\d+)$', ipv6_address)
                if ipv6_match:
                    interface['IPADDRESS6'] = ipv6_match.group(1)
                    interface['IPMASK6'] = get_network_mask_ipv6(int(ipv6_match.group(2)))
                
                interfaces.append(interface)
        
        return interfaces
