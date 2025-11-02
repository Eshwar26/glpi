#!/usr/bin/env python3
"""
GLPI Agent Task Inventory HPUX Uptime - Python Implementation
"""

import re
from typing import Any, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_first_match, Uname


class Uptime(InventoryModule):
    """HP-UX uptime detection module."""
    
    category = "hardware"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('uptime') and can_run('uname')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        
        arch = Uname('-m')
        uptime = Uptime._get_uptime(command='uptime')
        
        if inventory:
            inventory.set_hardware({
                'DESCRIPTION': f"{arch}/{uptime}"
            })
    
    @staticmethod
    def _get_uptime(**params) -> int:
        """Parse uptime command output and return seconds."""
        result = get_first_match(
            pattern=r'up \s (?:(\d+)\sdays\D+)? (\d{1,2}) : (\d{1,2})',
            **params
        )
        
        if not result:
            return 0
        
        # Result is a tuple: (days, hours, minutes)
        # Some might be None if not matched
        days_str = result[0] if len(result) > 0 else None
        hours_str = result[1] if len(result) > 1 else None
        minutes_str = result[2] if len(result) > 2 else None
        
        uptime = 0
        
        if days_str:
            try:
                uptime += int(days_str) * 24 * 3600
            except (ValueError, TypeError):
                pass
        
        if hours_str:
            try:
                uptime += int(hours_str) * 3600
            except (ValueError, TypeError):
                pass
        
        if minutes_str:
            try:
                uptime += int(minutes_str) * 60
            except (ValueError, TypeError):
                pass
        
        return uptime
