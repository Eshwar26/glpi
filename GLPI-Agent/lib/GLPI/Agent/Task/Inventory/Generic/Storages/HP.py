#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Storages HP - Python Implementation
"""

import platform
from typing import Any

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run
from GLPI.Agent.Tools.Storages.HP import hp_inventory


class HP(InventoryModule):
    """HP RAID controller inventory module."""
    
    run_me_if_these_checks_failed = ['GLPI.Agent.Task.Inventory.Generic.Storages.HpWithSmartctl']
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        # MSWin32 has its Win32.Storages.HP dedicated module
        return can_run('hpacucli') and platform.system() != 'Windows'
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        hp_inventory(path='hpacucli', **params)
