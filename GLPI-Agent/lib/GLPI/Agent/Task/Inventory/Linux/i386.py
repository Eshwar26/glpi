#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux i386 - Python Implementation
"""

import platform
import re
from typing import Any

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import Uname


class i386(InventoryModule):
    """i386/x86_64 architecture detection module."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        if params.get('remote'):
            machine = Uname('-m')
            return re.match(r'^(i\d86|x86_64)', machine) is not None
        return re.match(r'^(i\d86|x86_64)', platform.machine()) is not None
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        pass
