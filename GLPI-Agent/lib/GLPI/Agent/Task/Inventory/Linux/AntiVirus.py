#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux AntiVirus - Python Implementation
"""

from typing import Any

from GLPI.Agent.Task.Inventory.Module import InventoryModule


class AntiVirus(InventoryModule):
    """Base Linux antivirus detection module."""
    
    category = "antivirus"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return True
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection - placeholder."""
        pass
