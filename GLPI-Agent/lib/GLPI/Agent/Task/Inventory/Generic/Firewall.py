# glpi_agent/task/inventory/generic/firewall.py

from glpi_agent.task.inventory.module import InventoryModule


class Firewall(InventoryModule):
    """Generic Firewall inventory module."""
    
    @staticmethod
    def category():
        return "firewall"
    
    def is_enabled(self, **params):
        return True
    
    def do_inventory(self, **params):
        pass