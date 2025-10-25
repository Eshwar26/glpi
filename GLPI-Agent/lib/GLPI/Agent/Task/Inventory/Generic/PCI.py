# glpi_agent/task/inventory/generic/pci.py

from glpi_agent.task.inventory.module import InventoryModule
from glpi_agent.tools import can_run


class PCI(InventoryModule):
    """Generic PCI inventory module."""
    
    def is_enabled(self, **params):
        return can_run('lspci')
    
    def do_inventory(self, **params):
        pass