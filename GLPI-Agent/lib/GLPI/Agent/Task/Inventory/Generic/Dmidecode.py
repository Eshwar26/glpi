# glpi_agent/task/inventory/generic/dmidecode.py

import platform

from glpi_agent.task.inventory.module import InventoryModule
from glpi_agent.tools import can_run
from glpi_agent.tools.generic import get_dmidecode_infos


class Dmidecode(InventoryModule):
    """Generic Dmidecode inventory module."""
    
    def is_enabled(self, **params):
        # don't run dmidecode on Win2003
        # http://forge.fusioninventory.org/issues/379
        if platform.system() == 'Windows':
            if params.get('remote'):
                return False
            
            try:
                import win32api
                os_name = win32api.GetVersionEx()[4]
                # Check if it's Windows Server 2003
                if os_name == 'Win2003':
                    return False
            except (ImportError, Exception):
                pass
        
        return can_run('dmidecode') and get_dmidecode_infos()
    
    def do_inventory(self, **params):
        pass