"""
GLPI Agent Task Inventory Win32 Module

Platform module for Windows systems.
"""

import platform


class Win32:
    """Windows platform inventory module"""
    
    run_after = ["GLPI.Agent.Task.Inventory.Generic"]
    
    @staticmethod
    def is_enabled() -> bool:
        """Check if module is enabled (Windows only)"""
        return platform.system() == 'Windows'
    
    @staticmethod
    def do_inventory(**params) -> None:
        """Execute the inventory (placeholder)"""
        pass
