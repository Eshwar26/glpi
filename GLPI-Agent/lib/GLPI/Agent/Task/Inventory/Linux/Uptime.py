#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux Uptime - Python Implementation
"""

import time
from typing import Any, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_read, get_first_match, get_formated_local_time


class Uptime(InventoryModule):
    """Linux uptime detection module."""
    
    category = "os"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_read('/proc/uptime')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        boottime = Uptime._get_boot_time(
            logger=logger,
            file='/proc/uptime'
        )
        if not boottime:
            return
        
        if inventory:
            inventory.set_operating_system({
                'BOOT_TIME': boottime
            })
    
    @staticmethod
    def _get_boot_time(**params) -> Optional[str]:
        """Calculate boot time from uptime."""
        current_time = time.time()
        uptime_str = get_first_match(
            pattern=r'^([0-9.]+)',
            **params
        )
        if not uptime_str:
            return None
        
        try:
            uptime = float(uptime_str)
            boot_timestamp = current_time - uptime
            return get_formated_local_time(boot_timestamp)
        except (ValueError, TypeError):
            return None
