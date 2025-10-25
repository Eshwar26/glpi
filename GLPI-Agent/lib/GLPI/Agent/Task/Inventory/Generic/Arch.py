# glpi_agent/task/inventory/generic/arch.py

from glpi_agent.task.inventory.module import InventoryModule
from glpi_agent.tools import can_run, get_first_line


class Arch(InventoryModule):
    """Generic Architecture inventory module."""
    
    @staticmethod
    def category():
        return "os"
    
    def is_enabled(self, **params):
        return can_run('arch')
    
    def do_inventory(self, **params):
        inventory = params.get('inventory')
        
        arch = get_first_line(command='arch')
        
        inventory.set_operating_system({
            'ARCH': arch
        })