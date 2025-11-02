#!/usr/bin/env python3
"""
GLPI Agent Task Inventory HPUX OS - Python Implementation
"""

from typing import Any

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import Uname, get_root_fs_birth


class OS(InventoryModule):
    """HP-UX OS information detection module."""
    
    category = "os"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return True
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        
        # Operating system information
        kernel_release = Uname('-r')
        
        os = {
            'NAME': 'HP-UX',
            'VERSION': kernel_release,
            'KERNEL_VERSION': kernel_release,
        }
        
        installdate = get_root_fs_birth(**params)
        if installdate:
            os['INSTALL_DATE'] = installdate
        
        if inventory:
            inventory.set_operating_system(os)
