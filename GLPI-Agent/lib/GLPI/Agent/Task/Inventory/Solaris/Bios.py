#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Solaris Bios - Python Implementation
"""

import re
import platform
from typing import Any, Optional, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines, get_first_line, Uname, first
from GLPI.Agent.Tools.Solaris import get_smbios, get_zone, get_prtconf_infos


class Bios(InventoryModule):
    """Solaris BIOS detection module."""
    
    category = "bios"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('showrev') or can_run('/usr/sbin/smbios')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        archname = Uname('-m') if inventory and inventory.get_remote() else platform.machine()
        arch = 'i386' if archname.startswith('i86pc') else 'sparc'
        
        bios = {}
        infos = None
        
        if can_run('showrev'):
            infos = Bios._parse_show_rev(logger=logger)
            if infos:
                bios['SMANUFACTURER'] = infos.get('Hardware provider')
        
        if get_zone() == 'global':
            if infos:
                bios['SMODEL'] = infos.get('Application architecture')
            
            if arch == 'i386':
                smbios = get_smbios(logger=logger)
                
                if smbios:
                    bios_infos = smbios.get('SMB_TYPE_BIOS', {})
                    bios['BMANUFACTURER'] = bios_infos.get('Vendor')
                    bios['BVERSION'] = bios_infos.get('Version String')
                    bios['BDATE'] = bios_infos.get('Release Date')
                    
                    system_infos = smbios.get('SMB_TYPE_SYSTEM', {})
                    bios['SMANUFACTURER'] = system_infos.get('Manufacturer')
                    bios['SMODEL'] = system_infos.get('Product')
                    bios['SKUNUMBER'] = system_infos.get('SKU Number')
                    
                    motherboard_infos = smbios.get('SMB_TYPE_BASEBOARD', {})
                    bios['MMODEL'] = motherboard_infos.get('Product')
                    bios['MSN'] = motherboard_infos.get('Serial Number')
                    bios['MMANUFACTURER'] = motherboard_infos.get('Manufacturer')
            else:
                # SPARC architecture
                info = get_prtconf_infos(logger=logger)
                if info:
                    # Find first hash value in info dict
                    root = first(lambda v: isinstance(v, dict), info.values())
                    if root:
                        bios['SMODEL'] = root.get('banner-name')
                        openprom = root.get('openprom', {})
                        version = openprom.get('version', '')
                        match = re.search(r'OBP \s+ ([\d.]+) \s+ (\d{4})/(\d{2})/(\d{2})', version, re.VERBOSE)
                        if match:
                            bios['BVERSION'] = match.group(1)
                            bios['BDATE'] = f"{match.group(4)}/{match.group(3)}/{match.group(2)}"
                
                command = '/opt/SUNWsneep/bin/sneep' if can_run('/opt/SUNWsneep/bin/sneep') else 'sneep'
                
                ssn = get_first_line(
                    command=command,
                    logger=logger
                )
                if ssn:
                    bios['SSN'] = ssn
        else:
            bios['SMODEL'] = 'Solaris Containers'
        
        if not bios:
            return
        
        if inventory:
            inventory.set_bios(bios)
    
    @staticmethod
    def _parse_show_rev(**params) -> Optional[Dict[str, str]]:
        """Parse showrev command output."""
        if 'command' not in params:
            params['command'] = 'showrev'
        
        lines = get_all_lines(**params)
        if not lines:
            return None
        
        infos = {}
        for line in lines:
            match = re.match(r'^ ([^:]+) : \s+ (\S+)', line, re.VERBOSE)
            if match:
                infos[match.group(1)] = match.group(2)
        
        return infos
