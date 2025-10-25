"""
GLPI Agent Task Inventory Solaris Module

Platform module for Solaris systems.
"""

import platform


class Solaris:
    """Solaris platform inventory module"""
    
    run_after = ["GLPI.Agent.Task.Inventory.Generic"]
    
    @staticmethod
    def is_enabled() -> bool:
        """Check if module is enabled (Solaris only)"""
        return platform.system().lower() == 'sunos'
    
    @staticmethod
    def do_inventory(**params) -> None:
        """Execute the inventory (placeholder)"""
        pass
