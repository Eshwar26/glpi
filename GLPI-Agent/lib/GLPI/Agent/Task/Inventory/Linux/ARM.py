#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux ARM - Python Implementation
"""

import platform
import re
from typing import Any

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import Uname


class ARM(InventoryModule):
    """ARM architecture detection module."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        if params.get('remote'):
            machine = Uname('-m')
            return re.match(r'^(arm|aarch64)', machine) is not None
        return re.match(r'^(arm|aarch64)', platform.machine()) is not None
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        pass
