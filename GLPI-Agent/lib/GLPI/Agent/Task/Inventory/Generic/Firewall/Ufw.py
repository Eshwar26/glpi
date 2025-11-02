#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Firewall Ufw - Python Implementation
"""

from typing import Any

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_first_match
from GLPI.Agent.Tools.Constants import STATUS_ON, STATUS_OFF


class Ufw(InventoryModule):
    """UFW firewall inventory module."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        # Ubuntu
        return can_run('ufw')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        firewall_status = Ufw._get_firewall_status(logger=logger)
        
        if inventory:
            inventory.add_entry(
                section='FIREWALL',
                entry={
                    'DESCRIPTION': 'ufw',
                    'STATUS': firewall_status
                }
            )
    
    @staticmethod
    def _get_firewall_status(**params) -> str:
        """Get UFW firewall status."""
        status = get_first_match(
            command='ufw status',
            pattern=r'^Status:\s*(\w+)$',
            **params
        )
        
        if status and status == 'active':
            return STATUS_ON
        else:
            return STATUS_OFF
