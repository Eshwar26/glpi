#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Dmidecode Bios - Python Implementation
"""

import re
from typing import Any, Dict, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import empty
from GLPI.Agent.Tools.Generic import get_dmidecode_infos


class Bios(InventoryModule):
    """Dmidecode BIOS inventory module."""
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "bios"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return True
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        bios = Bios._get_bios(logger=logger)
        
        if inventory:
            inventory.set_bios(bios)
    
    @staticmethod
    def _get_bios(**params) -> Dict[str, Optional[str]]:
        """Get BIOS information from dmidecode."""
        infos = get_dmidecode_infos(**params)
        
        bios_info = infos.get(0, [{}])[0]
        system_info = infos.get(1, [{}])[0]
        base_info = infos.get(2, [{}])[0]
        chassis_info = infos.get(3, [{}])[0]
        
        bios = {
            'BMANUFACTURER': bios_info.get('Vendor'),
            'BDATE': bios_info.get('Release Date'),
            'BVERSION': bios_info.get('Version'),
            'ASSETTAG': chassis_info.get('Asset Tag')
        }
        
        # Fix issue #311: system_info 'Version' is a better 'Product Name' for Lenovo systems
        if (system_info.get('Version') and system_info.get('Manufacturer') and
                re.match(r'^LENOVO$', system_info['Manufacturer'], re.IGNORECASE) and
                re.match(r'^(Think|Idea|Yoga|Netfinity|Netvista|Intelli)', system_info['Version'], re.IGNORECASE)):
            product_name = system_info['Version']
            system_info['Version'] = system_info.get('Product Name')
            system_info['Product Name'] = product_name
        
        bios['SMODEL'] = system_info.get('Product') or system_info.get('Product Name')
        bios['MMODEL'] = base_info.get('Product Name')
        bios['SKUNUMBER'] = system_info.get('SKU Number')
        
        bios['SMANUFACTURER'] = system_info.get('Manufacturer') or system_info.get('Vendor')
        bios['MMANUFACTURER'] = base_info.get('Manufacturer')
        
        bios['SSN'] = system_info.get('Serial Number')
        if not bios['SSN']:
            bios['SSN'] = chassis_info.get('Serial Number')
        bios['MSN'] = base_info.get('Serial Number')
        
        # Default content can be set with a sharp character at the end of ASSETTAG & SKUNUMBER
        # like on MacOS platform
        if bios.get('ASSETTAG') and bios['ASSETTAG'].endswith('Tag#'):
            del bios['ASSETTAG']
        if bios.get('SKUNUMBER') and bios['SKUNUMBER'].endswith('SKU#'):
            del bios['SKUNUMBER']
        
        # On VirtualBox, set SSN from system uuid
        if (bios.get('MMODEL') and bios['MMODEL'] == 'VirtualBox' and
                not bios.get('SSN') and not bios.get('MSN') and
                not empty(system_info.get('UUID'))):
            bios['SSN'] = system_info['UUID'].lower()
        
        return bios
