# glpi_agent/task/inventory/generic/ipmi.py

from glpi_agent.task.inventory.module import InventoryModule
from glpi_agent.tools import can_run


class Ipmi(InventoryModule):
    """Generic IPMI inventory module."""
    
    def is_enabled(self, **params):
        return can_run('ipmitool')
    
    def do_inventory(self, **params):
        pass