#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux Networks FibreChannel - Python Implementation
"""

import re
from typing import Any, List, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines, get_canonical_interface_speed


class FibreChannel(InventoryModule):
    """Fibre Channel network interface detection module."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('systool')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        interfaces = FibreChannel._get_interfaces_from_fc_host(logger=logger)
        
        for interface in interfaces:
            if inventory:
                inventory.add_entry(
                    section='NETWORKS',
                    entry=interface
                )
    
    @staticmethod
    def _get_interfaces_from_fc_host(**params) -> List[Dict[str, Any]]:
        """Get Fibre Channel interfaces from fc_host."""
        if 'command' not in params:
            params['command'] = 'systool -c fc_host -v'
        
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        interfaces = []
        interface = None
        
        for line in lines:
            class_match = re.search(r'Class Device = "(.+)"', line)
            if class_match:
                interface = {
                    'DESCRIPTION': class_match.group(1),
                    'TYPE': 'fibrechannel'
                }
            elif interface:
                wwn_match = re.search(r'port_name\s+= "0x(\w+)"', line)
                if wwn_match:
                    # Convert hex string to WWN format (e.g., "50:01:43:80:03:6e:e1:c0")
                    wwn_hex = wwn_match.group(1)
                    wwn_parts = [wwn_hex[i:i+2] for i in range(0, len(wwn_hex), 2)]
                    interface['WWN'] = ':'.join(wwn_parts)
                
                state_match = re.search(r'port_state\s+= "(\w+)"', line)
                if state_match:
                    state = state_match.group(1)
                    if state == 'Online':
                        interface['STATUS'] = 'Up'
                    elif state == 'Linkdown':
                        interface['STATUS'] = 'Down'
                
                speed_match = re.search(r'speed\s+= "(.+)"', line)
                if speed_match:
                    speed = speed_match.group(1)
                    if speed != 'unknown':
                        interface['SPEED'] = get_canonical_interface_speed(speed)
                    
                    interfaces.append(interface)
                    interface = None
        
        return interfaces
