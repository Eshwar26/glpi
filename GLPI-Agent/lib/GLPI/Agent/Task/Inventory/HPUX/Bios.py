#!/usr/bin/env python3
"""
GLPI Agent Task Inventory HPUX Bios - Python Implementation
"""

import re
from typing import Any, Optional, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_first_line, get_all_lines, get_first_match
from GLPI.Agent.Tools.HPUX import get_info_from_machinfo


class Bios(InventoryModule):
    """HP-UX BIOS detection module."""
    
    category = "bios"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('model')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        model = get_first_line(command='model')
        
        version = None
        serial = None
        
        if can_run('/usr/contrib/bin/machinfo'):
            info = get_info_from_machinfo(logger=logger)
            if info:
                firmware_info = info.get('Firmware info', {})
                platform_info = info.get('Platform info', {})
                version = firmware_info.get('firmware revision')
                serial = platform_info.get('machine serial number')
        else:
            # Use cstm for older HP-UX systems
            lines = get_all_lines(
                command="echo 'sc product cpu;il' | /usr/sbin/cstm",
                logger=logger
            )
            if lines:
                for line in lines:
                    if 'PDC Firmware' not in line:
                        continue
                    match = re.search(r'Revision:\s+(\S+)', line)
                    if match:
                        version = f"PDC {match.group(1)}"
                        break
            
            serial = get_first_match(
                logger=logger,
                command="echo 'sc product system;il' | /usr/sbin/cstm",
                pattern=r'^System Serial Number:\s+: (\S+)'
            )
        
        if inventory:
            inventory.set_bios({
                'BVERSION': version,
                'BMANUFACTURER': 'HP',
                'SMANUFACTURER': 'HP',
                'SMODEL': model,
                'SSN': serial,
            })
