# glpi_agent/task/inventory/generic/hostname.py

import platform

from glpi_agent.task.inventory.module import InventoryModule
from glpi_agent.tools.hostname import get_hostname


class Hostname(InventoryModule):
    """Generic Hostname inventory module."""
    
    @staticmethod
    def category():
        return "hardware"
    
    def is_enabled(self, **params):
        # We use WMI for Windows because of charset issue
        return platform.system() != 'Windows'
    
    def do_inventory(self, **params):
        inventory = params.get('inventory')
        assetname_support = params.get('assetname_support', 0)
        
        # use the hostname as desired
        if assetname_support == 2:
            hostname = get_hostname()
        elif assetname_support == 3:
            hostname = get_hostname(fqdn=True)
        else:
            hostname = get_hostname(short=True)
        
        inventory.set_hardware({'NAME': hostname})