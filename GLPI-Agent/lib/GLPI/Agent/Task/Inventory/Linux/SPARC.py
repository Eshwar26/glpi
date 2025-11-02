#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux SPARC - Python Implementation
"""

import platform
from typing import Any

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import Uname


class SPARC(InventoryModule):
    """SPARC architecture detection module."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        if params.get('remote'):
            return Uname('-m').startswith('sparc')
        return platform.machine().startswith('sparc')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        pass
