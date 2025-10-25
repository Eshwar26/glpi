# glpi_agent/task/inventory/generic/networks.py

from glpi_agent.task.inventory.module import InventoryModule


class Networks(InventoryModule):
    """Generic Networks inventory module."""
    
    @staticmethod
    def category():
        return "network"
    
    def is_enabled(self, **params):
        return True
    
    def do_inventory(self, **params):
        pass
    