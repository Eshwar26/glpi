#!/usr/bin/env python3
"""
GLPI Agent Task Inventory BSD OS - Python Implementation
"""

import platform
from typing import Any

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import uname, get_first_match, can_run, get_formatted_local_time


class OS(InventoryModule):
    """BSD OS inventory module."""
    
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
        
        # basic operating system informations
        kernel_release = uname("-r")
        kernel_version = uname("-v")
        
        boottime_str = get_first_match(
            logger=logger,
            command="sysctl -n kern.boottime",
            pattern=r'sec = (\d+)'
        )
        
        boottime = None
        if boottime_str:
            try:
                boottime = int(boottime_str)
            except ValueError:
                pass
        
        # Get OS name
        if can_run('lsb_release'):
            name = get_first_match(
                logger=logger,
                command='lsb_release -d',
                pattern=r'Description:\s+(.+)'
            )
        else:
            # Use platform.system() as fallback
            name = platform.system()
        
        os_info = {
            'NAME': name,
            'FULL_NAME': platform.system(),
            'VERSION': kernel_release,
            'KERNEL_VERSION': kernel_version,
        }
        
        if boottime is not None:
            os_info['BOOT_TIME'] = get_formatted_local_time(boottime)
        
        if inventory:
            inventory.set_operating_system(os_info)
