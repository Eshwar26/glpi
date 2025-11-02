#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Remote_Mgmt RustDesk - Python Implementation

Based on the work done by Ilya published on no more existing https://fusioninventory.userecho.com site
"""

import platform
import re
from typing import Any, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import has_file, get_first_match, can_run, get_first_line, empty


class RustDesk(InventoryModule):
    """RustDesk remote management inventory module."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return has_file(RustDesk._get_rustdesk_config())
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        conf = RustDesk._get_rustdesk_config()
        rustdesk_id = get_first_match(
            file=conf,
            logger=logger,
            pattern=r"^id\s*=\s*'(.*)'$"
        )
        
        # Add support for --get-id parameter available since RustDesk 1.2 as id becomes empty in conf
        # Only works starting with RustDesk v1.2.2
        if not rustdesk_id or not rustdesk_id.strip():
            command = 'rustdesk'
            if platform.system() == 'Windows':
                from GLPI.Agent.Tools.Win32 import get_registry_value
                install_location = get_registry_value(
                    path='HKEY_LOCAL_MACHINE/SOFTWARE/Microsoft/Windows/CurrentVersion/Uninstall/RustDesk/InstallLocation',
                    logger=logger
                )
                base_path = r'C:\Program Files\RustDesk' if empty(install_location) else install_location
                command = f'{base_path}\\rustdesk.exe'
            
            if can_run(command):
                if platform.system() == 'Windows':
                    command = f'"{command}"'
                
                required = True
                version = get_first_line(
                    command=f'{command} --version',
                    logger=logger
                )
                if version:
                    match = re.match(r'^(\d+)\.(\d+)\.(\d+)', version)
                    if match:
                        major, minor, patch = map(int, match.groups())
                        required = not (major > 1 or (major == 1 and minor > 2) or (major == 1 and minor == 2 and patch >= 2))
                
                if required:
                    if logger:
                        logger.debug("Can't get RustDesk ID, at least RustDesk v1.2.2 is required")
                    return
                
                rustdesk_id = get_first_match(
                    command=f'{command} --get-id',
                    logger=logger,
                    pattern=r'^(\d+)$'
                )
                if not rustdesk_id:
                    if logger:
                        logger.debug("Can't get RustDesk ID, RustDesk is probably not running")
                    return
        
        if rustdesk_id:
            if logger:
                logger.debug(f'Found RustDesk ID : {rustdesk_id}')
            
            if inventory:
                inventory.add_entry(
                    section='REMOTE_MGMT',
                    entry={
                        'ID': rustdesk_id,
                        'TYPE': 'rustdesk'
                    }
                )
        else:
            if logger:
                logger.debug(f'RustDesk ID not found in {conf}')
    
    @staticmethod
    def _get_rustdesk_config() -> str:
        """Get RustDesk configuration file path."""
        if platform.system() == 'Windows':
            return r'C:\Windows\ServiceProfiles\LocalService\AppData\Roaming\RustDesk\config\RustDesk.toml'
        else:
            return '/root/.config/rustdesk/RustDesk.toml'
