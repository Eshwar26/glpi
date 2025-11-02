#!/usr/bin/env python3
"""
GLPI Agent Task Inventory BSD i386 - Python Implementation
"""

import re
import platform
from typing import Any

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import uname, get_first_line, get_canonical_speed
from GLPI.Agent.Tools.Generic import get_dmidecode_infos


class i386(InventoryModule):
    """BSD i386/x86_64 inventory module."""
    
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
            return bool(uname_m and re.match(r'^(i\d86|x86_64|amd64)', uname_m))
        
        # Check architecture
        arch = platform.machine()
        return bool(re.match(r'^(i\d86|x86_64)', arch))
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        no_category = params.get('no_category', {})
        
        # sysctl infos
        smodel = get_first_line(command='sysctl -n hw.model')
        bios = {
            'SMODEL': smodel
        }
        
        machine = get_first_line(command='sysctl -n hw.machine')
        
        # Get speed from model string
        speed = None
        if smodel:
            parts = smodel.split()
            speeds = [get_canonical_speed(part) for part in parts]
            speeds = [s for s in speeds if s is not None]
            if speeds:
                speed = speeds[-1]
        
        cpu = {
            'NAME': machine,
        }
        if speed:
            cpu['SPEED'] = speed
        
        count_str = get_first_line(command='sysctl -n hw.ncpu')
        count = int(count_str) if count_str and count_str.isdigit() else 0
        
        if inventory:
            inventory.set_bios(bios)
        
        # don't deal with CPUs if information can be computed from dmidecode
        infos = get_dmidecode_infos(logger=logger)
        if infos and infos.get(4):
            return
        
        if no_category.get('cpu'):
            return
        
        # Add CPU entries
        for _ in range(count):
            if inventory:
                inventory.add_entry(
                    section='CPUS',
                    entry=cpu
                )
