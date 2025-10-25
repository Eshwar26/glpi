"""
GLPI Agent Task Inventory AIX Module

Platform module for AIX systems.
"""

import platform


class AIX:
    """AIX platform inventory module"""
    
    run_after = ["GLPI.Agent.Task.Inventory.Generic"]
    
    @staticmethod
    def is_enabled() -> bool:
        """Check if module is enabled (AIX only)"""
        return platform.system().lower() == 'aix'
    
    @staticmethod
    def do_inventory(**params) -> None:
        """Execute the inventory (placeholder)"""
        pass
