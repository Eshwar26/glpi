#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Remote_Mgmt TeamViewer - Python Implementation
"""

import platform
import re
from typing import Any, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_first_line, get_first_match, hex2dec, glob_files


class TeamViewer(InventoryModule):
    """TeamViewer remote management inventory module."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        osname = platform.system()
        logger = params.get('logger')
        
        if osname == 'Windows':
            from GLPI.Agent.Tools.Win32 import get_registry_key, is64bit
            
            key = get_registry_key(
                path='HKEY_LOCAL_MACHINE/SOFTWARE/TeamViewer',
                required=['ClientID'],
                maxdepth=1,
                logger=logger
            )
            if not key and is64bit():
                key = get_registry_key(
                    path='HKEY_LOCAL_MACHINE/SOFTWARE/Wow6432Node/TeamViewer',
                    required=['ClientID'],
                    maxdepth=1,
                    logger=logger
                )
            
            return bool(key and len(key) > 0)
        
        elif osname == 'Darwin':
            return can_run('defaults') and bool(glob_files(
                "/Library/Preferences/com.teamviewer.teamviewer*.plist"
            ))
        
        return can_run('teamviewer')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        teamviewer_id = TeamViewer._get_id(
            osname=platform.system(),
            logger=logger
        )
        
        if teamviewer_id:
            if logger:
                logger.debug(f'Found TeamViewerID : {teamviewer_id}')
            
            if inventory:
                inventory.add_entry(
                    section='REMOTE_MGMT',
                    entry={
                        'ID': teamviewer_id,
                        'TYPE': 'teamviewer'
                    }
                )
        else:
            if logger:
                logger.debug('TeamViewerID not found')
    
    @staticmethod
    def _get_id(**params) -> Optional[str]:
        """Get TeamViewer ID based on OS."""
        osname = params.pop('osname', '')
        
        if osname == 'Windows':
            return TeamViewer._get_id_mswin32()
        elif osname == 'Darwin':
            return TeamViewer._get_id_darwin(**params)
        
        return TeamViewer._get_id_teamviewer_info(**params)
    
    @staticmethod
    def _get_id_mswin32() -> Optional[str]:
        """Get TeamViewer ID from Windows registry."""
        from GLPI.Agent.Tools.Win32 import get_registry_value, get_registry_key, is64bit
        
        clientid = get_registry_value(
            path='HKEY_LOCAL_MACHINE/SOFTWARE/TeamViewer/ClientID'
        )
        if not clientid and is64bit():
            clientid = get_registry_value(
                path='HKEY_LOCAL_MACHINE/SOFTWARE/Wow6432Node/TeamViewer/ClientID'
            )
        
        if not clientid:
            teamviewer_reg = get_registry_key(
                path='HKEY_LOCAL_MACHINE/SOFTWARE/TeamViewer',
                required=['ClientID']
            )
            if not teamviewer_reg and is64bit():
                teamviewer_reg = get_registry_key(
                    path='HKEY_LOCAL_MACHINE/SOFTWARE/Wow6432Node/TeamViewer',
                    required=['ClientID']
                )
            
            if not teamviewer_reg:
                return None
            
            # Look for subkey beginning with Version
            for key in teamviewer_reg.keys():
                if re.match(r'^Version\d+/', key):
                    clientid = teamviewer_reg[key].get('/ClientID')
                    if clientid:
                        break
        
        return hex2dec(clientid) if clientid else None
    
    @staticmethod
    def _get_id_darwin(**params) -> Optional[str]:
        """Get TeamViewer ID from macOS plist."""
        plist_files = params.get('darwin_glob') or glob_files(
            "/Library/Preferences/com.teamviewer.teamviewer*.plist"
        )
        
        if not plist_files:
            return None
        
        plist_file = plist_files[0]
        
        return get_first_line(
            command=f'defaults read {plist_file} ClientID',
            **params
        )
    
    @staticmethod
    def _get_id_teamviewer_info(**params) -> Optional[str]:
        """Get TeamViewer ID from teamviewer --info command."""
        return get_first_match(
            command='teamviewer --info',
            pattern=r'TeamViewer ID:(?:\033\[0m|\s)*(\d+)',
            **params
        )
