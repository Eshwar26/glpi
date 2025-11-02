#!/usr/bin/env python3
"""
GLPI Agent Task Inventory BSD Alpha - Python Implementation
"""

import re
import platform
from typing import Any, Dict, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import uname, get_first_line, get_all_lines


class Alpha(InventoryModule):
    """BSD Alpha inventory module."""
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "bios"
    
    @staticmethod
    def other_categories():
        """Return other categories this module handles."""
        return ['cpu']
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        remote = params.get('remote')
        if remote:
            uname_m = uname("-m")
            return bool(uname_m and re.match(r'^alpha', uname_m))
        
        # Check architecture
        arch = platform.machine()
        return bool(re.match(r'^alpha', arch))
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        no_category = params.get('no_category', {})
        
        bios = {
            'SMANUFACTURER': 'DEC',
        }
        
        # sysctl infos
        # example on *BSD: AlphaStation 255 4/232
        smodel = get_first_line(command='sysctl -n hw.model')
        if smodel:
            bios['SMODEL'] = smodel
        
        count_str = get_first_line(command='sysctl -n hw.ncpu')
        count = int(count_str) if count_str and count_str.isdigit() else 0
        
        # dmesg infos
        # NetBSD:
        # AlphaStation 255 4/232, 232MHz, s/n
        # cpu0 at mainbus0: ID 0 (primary), 21064A-2
        # OpenBSD:
        # AlphaStation 255 4/232, 232MHz
        # cpu0 at mainbus0: ID 0 (primary), 21064A-2 (pass 1.1)
        # FreeBSD:
        # AlphaStation 255 4/232, 232MHz
        # CPU: EV45 (21064A) major=6 minor=2
        
        cpu: Dict[str, Any] = {}
        dmesg_lines = get_all_lines(command='dmesg')
        if dmesg_lines:
            smodel_pattern = bios.get('SMODEL', '')
            for line in dmesg_lines:
                if smodel_pattern:
                    match = re.search(rf'{re.escape(smodel_pattern)},\s*(\S+)\s*MHz', line)
                    if match:
                        cpu['SPEED'] = match.group(1)
                
                match = re.match(r'^cpu[^:]*:\s*(.*)$', line, re.IGNORECASE)
                if match:
                    cpu['NAME'] = match.group(1)
        
        if inventory:
            inventory.set_bios(bios)
        
        if no_category.get('cpu'):
            return
        
        # Add CPU entries
        for _ in range(count):
            if inventory:
                inventory.add_entry(
                    section='CPUS',
                    entry=cpu
                )
