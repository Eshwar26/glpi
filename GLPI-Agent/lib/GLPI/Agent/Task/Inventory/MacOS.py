"""
GLPI Agent Task Inventory MacOS Module

Platform module for macOS/Darwin systems.
"""

import platform


class MacOS:
    """macOS platform inventory module"""
    
    run_after = ["GLPI.Agent.Task.Inventory.Generic"]
    
    @staticmethod
    def is_enabled() -> bool:
        """Check if module is enabled (macOS/Darwin only)"""
        return platform.system() == 'Darwin'
    
    @staticmethod
    def do_inventory(**params) -> None:
        """Execute the inventory (placeholder)"""
        pass
