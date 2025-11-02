#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux Distro - Python Implementation
"""

from typing import Any

from GLPI.Agent.Task.Inventory.Module import InventoryModule


class Distro(InventoryModule):
    """Base Linux distribution detection module."""
    
    category = "os"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return True
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection - placeholder."""
        pass
