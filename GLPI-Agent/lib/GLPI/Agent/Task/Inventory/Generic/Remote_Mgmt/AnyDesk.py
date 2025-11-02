#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Remote_Mgmt AnyDesk - Python Implementation

Based on the work done by Ilya published on no more existing https://fusioninventory.userecho.com site
"""

import platform
from typing import Any, List

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import has_folder, glob_files, can_read, get_first_match


class AnyDesk(InventoryModule):
    """AnyDesk remote management inventory module."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        configs = AnyDesk._get_anydesk_config()
        return bool(configs)
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        for conf in AnyDesk._get_anydesk_config():
            anydesk_id = get_first_match(
                file=conf,
                logger=logger,
                pattern=r'^ad\.anynet\.id=(\S+)'
            )
            
            if anydesk_id:
                if logger:
                    logger.debug(f'Found AnyDesk ID : {anydesk_id}')
                
                if inventory:
                    inventory.add_entry(
                        section='REMOTE_MGMT',
                        entry={
                            'ID': anydesk_id,
                            'TYPE': 'anydesk'
                        }
                    )
            else:
                if logger:
                    logger.debug(f'AnyDesk ID not found in {conf}')
    
    @staticmethod
    def _get_anydesk_config() -> List[str]:
        """Get AnyDesk configuration file paths."""
        configs = []
        
        if platform.system() == 'Windows':
            if has_folder(r'C:\ProgramData\AnyDesk'):
                configs.extend(glob_files(r'C:\ProgramData\AnyDesk\ad_*\system.conf'))
                configs.append(r'C:\ProgramData\AnyDesk\system.conf')
        else:
            configs.extend(glob_files('/etc/anydesk_ad_*/system.conf'))
            configs.append('/etc/anydesk/system.conf')
        
        return [c for c in configs if can_read(c)]
