#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux PowerPC Bios - Python Implementation
"""

import re
from typing import Any

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import get_first_line


class Bios(InventoryModule):
    """PowerPC BIOS detection module."""
    
    category = "bios"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return True
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        
        bios = {}
        
        ssn = get_first_line(file='/proc/device-tree/serial-number')
        if ssn:
            # Remove some unprintable chars
            bios['SSN'] = re.sub(r'[^\,^\.^\w^\ ]', '', ssn)
        
        smodel = get_first_line(file='/proc/device-tree/model')
        if smodel:
            smodel = re.sub(r'[^\,^\.^\w^\ ]', '', smodel)
            
            color_code = get_first_line(file='/proc/device-tree/color-code')
            if color_code:
                # Unpack color code
                try:
                    color = color_code.encode('latin-1').hex()[:7]
                    if color:
                        smodel += f" color: {color}"
                except Exception:
                    pass
            
            bios['SMODEL'] = smodel
        
        bversion = get_first_line(file='/proc/device-tree/openprom/model')
        if bversion:
            bios['BVERSION'] = re.sub(r'[^\,^\.^\w^\ ]', '', bversion)
        
        copyright_text = get_first_line(file='/proc/device-tree/copyright')
        if copyright_text and 'Apple' in copyright_text:
            # What about the Apple clone?
            bios['BMANUFACTURER'] = 'Apple Computer, Inc.'
            bios['SMANUFACTURER'] = 'Apple Computer, Inc.'
        
        if inventory:
            inventory.set_bios(bios)
