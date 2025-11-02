#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Remote_Mgmt RMS - Python Implementation
"""

import platform
from typing import Any, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import hex2dec


class RMS(InventoryModule):
    """Remote Utilities (RMS) remote management inventory module."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        if platform.system() != 'Windows':
            return False
        
        from GLPI.Agent.Tools.Win32 import get_registry_key
        
        key = get_registry_key(
            path='HKEY_LOCAL_MACHINE/SOFTWARE/Usoris/Remote Utilities Host/Host/Parameters',
            required=['InternetId'],
            maxdepth=1,
        )
        
        return bool(key and len(key) > 0)
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        internet_id = RMS._get_id(logger=logger)
        
        if internet_id:
            if logger:
                logger.debug(f'Found InternetID : {internet_id}')
            
            if inventory:
                inventory.add_entry(
                    section='REMOTE_MGMT',
                    entry={
                        'ID': internet_id,
                        'TYPE': 'rms'
                    }
                )
        else:
            if logger:
                logger.debug('InternetID not found')
    
    @staticmethod
    def _get_id(**params) -> Optional[str]:
        """Get RMS Internet ID."""
        from GLPI.Agent.Tools.Win32 import get_registry_value
        from GLPI.Agent.XML import XML
        
        internetid = get_registry_value(
            path='HKEY_LOCAL_MACHINE/SOFTWARE/Usoris/Remote Utilities Host/Host/Parameters/InternetId',
            **params
        )
        
        if not internetid:
            return None
        
        internetid = hex2dec(internetid)
        
        tree = XML(string=internetid).dump_as_hash()
        
        if not tree or 'rms_internet_id_settings' not in tree:
            return None
        
        return tree['rms_internet_id_settings'].get('internet_id')
