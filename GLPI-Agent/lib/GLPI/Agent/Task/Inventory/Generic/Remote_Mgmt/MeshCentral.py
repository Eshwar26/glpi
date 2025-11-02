#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Remote_Mgmt MeshCentral - Python Implementation
"""

import platform
from typing import Any, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, glob_files, has_file, get_first_line


class MeshCentral(InventoryModule):
    """MeshCentral remote management inventory module."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        osname = platform.system()
        logger = params.get('logger')
        
        if osname == 'Windows':
            from GLPI.Agent.Tools.Win32 import get_registry_key
            
            key = get_registry_key(
                path='HKEY_LOCAL_MACHINE/SOFTWARE/Open Source/',
                required=['NodeId'],
                maxdepth=2,
                logger=logger
            )
            
            return bool(key and key.get('Mesh Agent/') and len(key['Mesh Agent/']) > 0)
        
        elif osname == 'Darwin':
            return can_run('defaults') and bool(glob_files(
                "/Library/LaunchDaemons/meshagent*.plist"
            ))
        
        return osname == 'Linux' and has_file('/etc/systemd/system/meshagent.service')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        node_id = MeshCentral._get_node_id(logger=logger)
        if not node_id:
            return
        
        if inventory:
            inventory.add_entry(
                section='REMOTE_MGMT',
                entry={
                    'ID': node_id,
                    'TYPE': 'meshcentral'
                }
            )
    
    @staticmethod
    def _get_node_id(**params) -> Optional[str]:
        """Get MeshCentral Node ID."""
        osname = platform.system()
        
        if osname == 'Windows':
            return MeshCentral._win_based(**params)
        elif osname == 'Darwin':
            return MeshCentral._darwin_based(**params)
        else:
            return MeshCentral._linux_based(**params)
    
    @staticmethod
    def _win_based(**params) -> Optional[str]:
        """Get Node ID from Windows registry."""
        from GLPI.Agent.Tools.Win32 import get_registry_value
        
        return get_registry_value(
            path='HKEY_LOCAL_MACHINE/SOFTWARE/Open Source/Mesh Agent/NodeId',
            logger=params.get('logger')
        )
    
    @staticmethod
    def _linux_based(**params) -> Optional[str]:
        """Get Node ID from Linux systemd service."""
        command = get_first_line(
            file='/etc/systemd/system/meshagent.service',
            pattern=r'Ex.*=(.*)\s\-',
            logger=params.get('logger'),
        )
        
        if not command:
            return None
        
        return get_first_line(
            command=f'{command} -nodeid',
            logger=params.get('logger')
        )
    
    @staticmethod
    def _darwin_based(**params) -> Optional[str]:
        """Get Node ID from macOS meshagent."""
        return get_first_line(
            command='/usr/local/mesh_services/meshagent/meshagent_osx64 -nodeid',
            logger=params.get('logger')
        )
