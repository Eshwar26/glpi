#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Solaris Hardware - Python Implementation
"""

import platform
from typing import Any

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import get_first_line, Uname, empty
from GLPI.Agent.Tools.Solaris import get_smbios, get_zone


class Hardware(InventoryModule):
    """Solaris hardware detection module."""
    
    category = "hardware"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return True
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        kernel_arch = get_first_line(
            logger=logger,
            command='arch -k'
        )
        proct = Uname('-p')
        platform_info = Uname('-i')
        hostid = get_first_line(
            logger=logger,
            command='hostid'
        )
        description = f"{platform_info}({kernel_arch})/{proct} HostID={hostid}"
        
        hardware = {
            'DESCRIPTION': description
        }
        
        archname = Uname('-m') if inventory and inventory.get_remote() else platform.machine()
        arch = 'i386' if archname.startswith('i86pc') else 'sparc'
        
        if get_zone() == 'global':
            if arch == 'i386':
                infos = get_smbios(logger=logger)
                if infos and infos.get('SMB_TYPE_SYSTEM'):
                    hardware['UUID'] = infos['SMB_TYPE_SYSTEM'].get('UUID')
            else:
                hardware['UUID'] = Hardware._get_uuid(
                    command='/usr/sbin/zoneadm -z global list -p',
                    logger=logger
                )
                if empty(hardware.get('UUID')):
                    hardware['UUID'] = Hardware._get_uuid_global(logger=logger)
        elif arch == 'sparc':
            hardware['UUID'] = Hardware._get_uuid(logger=logger)
        
        if inventory:
            inventory.set_hardware(hardware)
    
    @staticmethod
    def _get_uuid_global(**params) -> str:
        """Get UUID from virtinfo for global zone."""
        if 'command' not in params:
            params['command'] = 'virtinfo -u'
        
        line = get_first_line(**params)
        if not line:
            return ''
        
        info = line.split(': ')
        if len(info) >= 2:
            return info[1]
        return ''
    
    @staticmethod
    def _get_uuid(**params) -> str:
        """Get UUID from zoneadm."""
        if 'command' not in params:
            params['command'] = '/usr/sbin/zoneadm list -p'
        
        line = get_first_line(**params)
        if not line:
            return ''
        
        info = line.split(':')
        if len(info) >= 5:
            return info[4]
        return ''
