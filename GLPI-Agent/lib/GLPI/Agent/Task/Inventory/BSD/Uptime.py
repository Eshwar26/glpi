#!/usr/bin/env python3
"""
GLPI Agent Task Inventory BSD Uptime - Python Implementation
"""

import re
import time
from typing import Any, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, uname, get_first_line


class Uptime(InventoryModule):
    """BSD Uptime inventory module."""
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "hardware"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('sysctl')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        
        arch = uname("-m")
        uptime = Uptime._get_uptime(command='sysctl -n kern.boottime')
        
        description = f"{arch}/{uptime}" if arch and uptime else arch or str(uptime)
        
        if inventory:
            inventory.set_hardware({
                'DESCRIPTION': description
            })
    
    @staticmethod
    def _get_uptime(**params) -> Optional[int]:
        """Get system uptime in seconds."""
        line = get_first_line(**params)
        if not line:
            return None
        
        # the output of 'sysctl -n kern.boottime' differs between BSD flavours
        boottime = None
        
        # OpenBSD format: starts with a number
        match = re.match(r'^(\d+)', line)
        if match:
            boottime = int(match.group(1))
        else:
            # FreeBSD format: sec = <number>
            match = re.search(r'sec = (\d+)', line)
            if match:
                boottime = int(match.group(1))
        
        if boottime is None:
            return None
        
        return int(time.time()) - boottime
