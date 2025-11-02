#!/usr/bin/env python3
"""
GLPI Agent Task Inventory AIX OS - Python Implementation
"""

import re
from typing import Any

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import uname, get_first_line


class OS(InventoryModule):
    """AIX OS inventory module."""
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "os"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return True
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        # Operating system informations
        kernel_name = uname("-s")
        
        version = get_first_line(
            logger=logger,
            command='oslevel'
        )
        
        if version:
            # Remove trailing .0
            version = re.sub(r'(\.0)*$', '', version)
        
        os_level = get_first_line(
            logger=logger,
            command='oslevel -s'
        )
        
        service_pack = None
        if os_level:
            os_level_parts = os_level.split('-')
            if len(os_level_parts) >= 4:
                # Add TL (Technology Level) to version unless it's 00
                if os_level_parts[1] != "00":
                    version = f"{version} TL{os_level_parts[1]}"
                
                service_pack = f"{os_level_parts[2]}-{os_level_parts[3]}"
        
        os_info = {
            'NAME': 'AIX',
            'FULL_NAME': f"{kernel_name} {version}" if kernel_name and version else 'AIX',
            'VERSION': version,
        }
        
        if service_pack:
            os_info['SERVICE_PACK'] = service_pack
        
        if inventory:
            inventory.set_operating_system(os_info)
