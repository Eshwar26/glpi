"""
GLPI Agent Task Inventory Linux Module

Platform module for Linux systems.
"""

import platform


class Linux:
    """Linux platform inventory module"""
    
    run_after = ["GLPI.Agent.Task.Inventory.Generic"]
    
    @staticmethod
    def is_enabled() -> bool:
        """Check if module is enabled (Linux only)"""
        return platform.system() == 'Linux'
    
    @staticmethod
    def do_inventory(**params) -> None:
        """Execute the inventory (placeholder)"""
        pass
