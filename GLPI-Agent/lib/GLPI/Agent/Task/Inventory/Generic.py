"""
GLPI Agent Task Inventory Generic Module

Generic platform module that runs on all systems.
"""


class Generic:
    """Generic platform inventory module"""
    
    @staticmethod
    def is_enabled() -> bool:
        """Check if module is enabled (always enabled)"""
        return True
    
    @staticmethod
    def do_inventory(**params) -> None:
        """Execute the inventory (placeholder)"""
        pass
