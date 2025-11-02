#!/usr/bin/env python3
"""
GLPI Agent Task Inventory AIX Drives - Python Implementation
"""

from typing import Dict, Any, List, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines
from GLPI.Agent.Tools.Unix import get_filesystems_from_df


class Drives(InventoryModule):
    """AIX Drives inventory module."""
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "drive"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('df')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        # get filesystems
        filesystems = get_filesystems_from_df(
            logger=logger,
            command='df -P -k'
        )
        
        types = Drives._get_filesystem_types(
            command='lsfs -c',
            logger=logger
        )
        
        # add filesystems to the inventory
        for filesystem in filesystems:
            if types and filesystem.get('TYPE'):
                filesystem['FILESYSTEM'] = types.get(filesystem['TYPE'])
            
            if inventory:
                inventory.add_entry(
                    section='DRIVES',
                    entry=filesystem
                )
    
    @staticmethod
    def _get_filesystem_types(**params) -> Optional[Dict[str, str]]:
        """Get filesystem types."""
        lines = get_all_lines(**params)
        if not lines:
            return None
        
        types = {}
        
        # skip headers
        if lines:
            lines = lines[1:]
        
        for line in lines:
            parts = line.split(':')
            if len(parts) >= 3:
                mountpoint = parts[0]
                fs_type = parts[2]
                types[mountpoint] = fs_type
        
        return types
