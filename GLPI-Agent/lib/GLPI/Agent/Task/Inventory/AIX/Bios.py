#!/usr/bin/env python3
"""
GLPI Agent Task Inventory AIX Bios - Python Implementation
"""

import re
from typing import Dict, Any, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import uname, get_first_match, first
from GLPI.Agent.Tools.AIX import get_lsvpd_infos, get_lsconf_infos


class Bios(InventoryModule):
    """AIX BIOS inventory module."""
    
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
        
        bios = Bios._get_infos(logger=logger)
        
        if inventory:
            inventory.set_bios(bios)
    
    @staticmethod
    def _get_infos(**params) -> Dict[str, str]:
        """Get BIOS information."""
        infos = get_lsvpd_infos(**params)
        
        bios = {
            'BMANUFACTURER': 'IBM',
            'SMANUFACTURER': 'IBM',
        }
        
        # Get the BIOS version from the System Microcode Image (MI) version, in
        # 'System Firmware' section of VPD, containing three space separated values:
        # - the microcode image the system currently runs
        # - the 'permanent' microcode image
        # - the 'temporary' microcode image
        # See http://www.systemscanaix.com/sample_reports/aix61/hardware_configuration.html
        
        system = first(lambda x: x.get('DS') == 'System Firmware', infos)
        if system:
            # we only return the currently booted firmware
            mi_value = system.get('MI', '')
            if mi_value:
                firmwares = mi_value.split()
                if firmwares:
                    bios['BVERSION'] = firmwares[0]
        
        vpd = first(lambda x: x.get('DS') == 'System VPD', infos)
        if vpd:
            bios['SSN'] = vpd.get('SE', '')
            bios['SMODEL'] = vpd.get('TM', '')
        
        # Use lsconf if lsvpd is not usable
        if not (bios.get('SSN') and bios.get('SMODEL') and bios.get('BVERSION')):
            lsconf = get_lsconf_infos(**params)
            if lsconf:
                bios['SSN'] = lsconf.get('Machine Serial Number', '')
                bios['BVERSION'] = lsconf.get('Platform Firmware level', '')
                system_model = lsconf.get('System Model', '')
                if system_model:
                    parts = system_model.split(',', 1)
                    if len(parts) >= 2:
                        bios['SMANUFACTURER'] = parts[0]
                        bios['SMODEL'] = parts[1]
                    elif parts:
                        bios['SMODEL'] = parts[0]
        
        uname_l = uname("-L")
        # LPAR partition can access the serial number of the host computer
        if bios.get('SSN') and uname_l:
            match = re.match(r'^(\d+)\s+\S+', uname_l)
            if match:
                name = match.group(1)
                logger = params.get('logger')
                lparname = get_first_match(
                    pattern=r'Partition\s+Name.*:\s+(.*)$',
                    logger=logger,
                    command="lparstat -i"
                )
                # But an lpar can be migrated between hosts then we don't use to not have
                # a SSN change during such migration. Anyway there's still a risk a given
                # lparname is also used on another AIX system, administrators should avoid
                # such usage as they won't be able to migrate the 2 LPARs on the same server
                if lparname:
                    bios['SSN'] = f"aixlpar-{bios['SSN']}-{lparname}"
                else:
                    bios['SSN'] = f"aixlpar-{bios['SSN']}-{name}"
        
        return bios
