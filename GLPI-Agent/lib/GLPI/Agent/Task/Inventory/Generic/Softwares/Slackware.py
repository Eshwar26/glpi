#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Softwares Slackware - Python Implementation
"""

import os
import re
from typing import Any

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run


class Slackware(InventoryModule):
    """Slackware package inventory module."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('pkgtool')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        directory = '/var/log/packages'
        
        try:
            if not os.path.isdir(directory):
                return
            
            for file in os.listdir(directory):
                match = re.match(
                    r'^(.+)-(.+)-(i[0-9]86|noarch|x86_64|x86|fw|npmjs)-(.*)$',
                    file
                )
                if not match:
                    continue
                
                name, version, arch = match.group(1), match.group(2), match.group(3)
                
                if inventory:
                    inventory.add_entry(
                        section='SOFTWARES',
                        entry={
                            'NAME': name,
                            'VERSION': version,
                            'ARCH': arch
                        }
                    )
        except (OSError, PermissionError) as e:
            if logger:
                logger.debug(f"Error reading {directory}: {e}")
