"""
GLPI Agent Task Inventory Virtualization Module

Detects and inventories virtualization information.
"""


class Virtualization:
    """Virtualization inventory module"""
    
    category = "virtualmachine"
    
    @staticmethod
    def is_enabled() -> bool:
        """Check if module is enabled (always enabled)"""
        return True
    
    @staticmethod
    def do_inventory(**params) -> None:
        """Execute the inventory (placeholder)"""
        pass
