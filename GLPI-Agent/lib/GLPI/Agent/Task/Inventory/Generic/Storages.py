# glpi_agent/task/inventory/generic/storages.py

from glpi_agent.task.inventory.module import InventoryModule


class Storages(InventoryModule):
    """Generic Storages inventory module."""
    
    @staticmethod
    def category():
        return "storage"
    
    def is_enabled(self, **params):
        return True
    
    def do_inventory(self, **params):
        pass