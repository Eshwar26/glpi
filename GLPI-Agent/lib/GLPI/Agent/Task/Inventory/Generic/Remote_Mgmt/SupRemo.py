#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Remote_Mgmt SupRemo - Python Implementation
"""

import platform
import re
from typing import Any, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_first_match, hex2dec


class SupRemo(InventoryModule):
    """Supremo remote management inventory module."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        if platform.system() == 'Windows':
            from GLPI.Agent.Tools.Win32 import get_registry_key, is64bit
            
            logger = params.get('logger')
            key = get_registry_key(
                path='HKEY_LOCAL_MACHINE/SOFTWARE/Supremo',
                required=['ClientID'],
                maxdepth=1,
                logger=logger
            )
            if not key and is64bit():
                key = get_registry_key(
                    path='HKEY_LOCAL_MACHINE/SOFTWARE/Wow6432Node/Supremo',
                    required=['ClientID'],
                    maxdepth=1,
                    logger=logger
                )
            
            return bool(key and len(key) > 0)
        
        return can_run('supremo')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        supremo_id = (
            SupRemo._get_id_mswin32(logger=logger)
            if platform.system() == 'Windows'
            else SupRemo._get_id_supremo_info(logger=logger)
        )
        
        if supremo_id:
            if logger:
                logger.debug(f'Found SupRemoID : {supremo_id}')
            
            if inventory:
                inventory.add_entry(
                    section='REMOTE_MGMT',
                    entry={
                        'ID': supremo_id,
                        'TYPE': 'supremo'
                    }
                )
        else:
            if logger:
                logger.debug('SupRemoID not found')
    
    @staticmethod
    def _get_id_mswin32(**params) -> Optional[str]:
        """Get Supremo ID from Windows registry."""
        from GLPI.Agent.Tools.Win32 import get_registry_value, get_registry_key, is64bit
        
        clientid = get_registry_value(
            path='HKEY_LOCAL_MACHINE/SOFTWARE/Supremo/ClientID'
        )
        if not clientid and is64bit():
            clientid = get_registry_value(
                path='HKEY_LOCAL_MACHINE/SOFTWARE/Wow6432Node/Supremo/ClientID'
            )
        
        if not clientid:
            supremover_reg = get_registry_key(
                path='HKEY_LOCAL_MACHINE/SOFTWARE/Supremo',
                required=['ClientID'],
                maxdepth=2,
            )
            if not supremover_reg and is64bit():
                supremover_reg = get_registry_key(
                    path='HKEY_LOCAL_MACHINE/SOFTWARE/Wow6432Node/Supremo',
                    required=['ClientID'],
                    maxdepth=2,
                )
            
            if not supremover_reg:
                return None
            
            # Look for subkey beginning with Version
            for key in supremover_reg.keys():
                if re.match(r'^Version\d+/', key):
                    clientid = supremover_reg[key].get('/ClientID')
                    if clientid:
                        break
        
        if not clientid:
            return None
        
        return f"{hex2dec(clientid):09d}"
    
    @staticmethod
    def _get_id_supremo_info(**params) -> Optional[str]:
        """Get Supremo ID from supremo --info command."""
        return get_first_match(
            command='supremo --info',
            pattern=r'SupRemo ID:(?:\033\[0m|\s)*(\d+)\s+',
            **params
        )
