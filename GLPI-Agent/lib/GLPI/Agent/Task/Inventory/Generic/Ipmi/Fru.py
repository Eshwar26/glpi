#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Ipmi Fru - Python Implementation
"""

from typing import Any

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run


class Fru(InventoryModule):
    """IPMI FRU inventory module (base class)."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('ipmitool')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        # Base module does nothing
        pass
