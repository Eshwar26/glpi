"""
GLPI Agent Task Inventory HPUX Module

Platform module for HP-UX systems.
"""

import platform


class HPUX:
    """HP-UX platform inventory module"""
    
    run_after = ["GLPI.Agent.Task.Inventory.Generic"]
    
    @staticmethod
    def is_enabled() -> bool:
        """Check if module is enabled (HP-UX only)"""
        return platform.system().lower() == 'hp-ux'
    
    @staticmethod
    def do_inventory(**params) -> None:
        """Execute the inventory (placeholder)"""
        pass
