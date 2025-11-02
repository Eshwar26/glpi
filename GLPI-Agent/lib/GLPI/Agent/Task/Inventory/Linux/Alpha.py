#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux Alpha - Python Implementation
"""

import platform
from typing import Any

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import Uname


class Alpha(InventoryModule):
    """Alpha architecture detection module."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        if params.get('remote'):
            return Uname('-m').startswith('alpha')
        return platform.machine().startswith('alpha')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        pass
