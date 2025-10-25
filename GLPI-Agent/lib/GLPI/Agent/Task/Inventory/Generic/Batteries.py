# glpi_agent/task/inventory/generic/batteries.py

from glpi_agent.task.inventory.module import InventoryModule


class Batteries(InventoryModule):
    """Generic Batteries inventory module."""
    
    @staticmethod
    def category():
        return "battery"
    
    def is_enabled(self, **params):
        return True
    
    def do_inventory(self, **params):
        pass