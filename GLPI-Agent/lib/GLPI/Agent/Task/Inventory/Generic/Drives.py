# glpi_agent/task/inventory/generic/drives.py

from glpi_agent.task.inventory.module import InventoryModule


class Drives(InventoryModule):
    """Generic Drives inventory module."""
    
    @staticmethod
    def category():
        return "drive"
    
    def is_enabled(self, **params):
        return True
    
    def do_inventory(self, **params):
        pass