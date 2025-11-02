#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Dmidecode Hardware - Python Implementation
"""

from typing import Any, Dict, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools.Generic import get_dmidecode_infos


class Hardware(InventoryModule):
    """Dmidecode Hardware inventory module."""
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "hardware"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return True
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        hardware = Hardware._get_hardware(logger=logger)
        
        if inventory and hardware:
            inventory.set_hardware(hardware)
    
    @staticmethod
    def _get_hardware(**params) -> Optional[Dict[str, Optional[str]]]:
        """Get hardware information from dmidecode."""
        infos = get_dmidecode_infos(**params)
        
        if not infos:
            return None
        
        system_info = infos.get(1, [{}])[0]
        chassis_info = infos.get(3, [{}])[0]
        
        hardware = {
            'UUID': system_info.get('UUID'),
            'CHASSIS_TYPE': chassis_info.get('Type')
        }
        
        return hardware
