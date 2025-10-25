# glpi_agent/task/inventory/generic/remote_mgmt.py

from glpi_agent.task.inventory.module import InventoryModule


class RemoteMgmt(InventoryModule):
    """Generic Remote Management inventory module."""
    
    @staticmethod
    def category():
        return "remote_mgmt"
    
    def is_enabled(self, **params):
        return True
    
    def do_inventory(self, **params):
        pass