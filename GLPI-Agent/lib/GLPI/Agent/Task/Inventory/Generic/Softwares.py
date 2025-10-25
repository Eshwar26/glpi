# glpi_agent/task/inventory/generic/softwares.py

from glpi_agent.task.inventory.module import InventoryModule


class Softwares(InventoryModule):
    """Generic Softwares inventory module."""
    
    @staticmethod
    def category():
        return "software"
    
    def is_enabled(self, **params):
        return True
    
    def do_inventory(self, **params):
        pass