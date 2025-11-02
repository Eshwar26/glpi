#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Remote_Mgmt LiteManager - Python Implementation
"""

import platform
from typing import Any, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import first


class LiteManager(InventoryModule):
    """LiteManager remote management inventory module."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        if platform.system() != 'Windows':
            return False
        
        from GLPI.Agent.Tools.Win32 import get_registry_key
        
        def check_path(path):
            key = get_registry_key(
                path=path,
                required=['ID (read only)'],
                maxdepth=3,
            )
            return key and len(key) > 0
        
        paths = [
            'HKEY_LOCAL_MACHINE/SYSTEM/LiteManager',
            'HKEY_LOCAL_MACHINE/SOFTWARE/LiteManager',
        ]
        
        return bool(first(check_path, paths))
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        litemanager_id = LiteManager._get_id(logger=logger)
        
        if litemanager_id:
            if logger:
                logger.debug(f'Found LiteManagerID : {litemanager_id}')
            
            if inventory:
                inventory.add_entry(
                    section='REMOTE_MGMT',
                    entry={
                        'ID': litemanager_id,
                        'TYPE': 'litemanager'
                    }
                )
        else:
            if logger:
                logger.debug('LiteManagerID not found')
    
    @staticmethod
    def _get_id(**params) -> Optional[str]:
        """Get LiteManager ID."""
        def find_in_path(path):
            return LiteManager._find_id(path=path, **params)
        
        paths = [
            'HKEY_LOCAL_MACHINE/SYSTEM/LiteManager',
            'HKEY_LOCAL_MACHINE/SOFTWARE/LiteManager',
        ]
        
        return first(find_in_path, paths)
    
    @staticmethod
    def _find_id(**params) -> Optional[str]:
        """Find LiteManager ID in registry."""
        from GLPI.Agent.Tools.Win32 import get_registry_key
        
        key = get_registry_key(
            required=['ID (read only)'],
            maxdepth=3,
            **params
        )
        
        if not key or not len(key):
            return None
        
        parameters = None
        
        for sub in [k for k in key.keys() if k.endswith('/')]:
            if not key[sub].get('Server/'):
                continue
            if not key[sub]['Server/'].get('Parameters/'):
                continue
            parameters = key[sub]['Server/']['Parameters/']
            if parameters.get('/ID (read only)'):
                break
        
        if not parameters:
            return None
        
        return parameters.get('/ID (read only)')
