# glpi_agent/task/inventory/generic/processes.py

import platform

from glpi_agent.task.inventory.module import InventoryModule
from glpi_agent.tools import can_run
from glpi_agent.tools.unix import get_processes


class Processes(InventoryModule):
    """Generic Processes inventory module."""
    
    @staticmethod
    def category():
        return "process"
    
    def is_enabled(self, **params):
        return platform.system() != 'Windows' and can_run('ps')
    
    def do_inventory(self, **params):
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        for process in get_processes(logger=logger):
            inventory.add_entry(
                section='PROCESSES',
                entry=process
            )