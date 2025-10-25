# glpi_agent/task/inventory/generic/os.py

import platform
import socket

from glpi_agent.task.inventory.module import InventoryModule
from glpi_agent.tools.hostname import get_remote_fqdn, get_remote_hostdomain


class OS(InventoryModule):
    """Generic OS inventory module."""
    
    @staticmethod
    def category():
        return "os"
    
    def is_enabled(self, **params):
        return True
    
    def do_inventory(self, **params):
        inventory = params.get('inventory')
        
        remote = inventory.get_remote()
        if remote:
            inventory.set_operating_system({
                'KERNEL_NAME': platform.system(),
                'FQDN': get_remote_fqdn(),
                'DNS_DOMAIN': get_remote_hostdomain(),
            })
        else:
            inventory.set_operating_system({
                'KERNEL_NAME': platform.system(),
                'FQDN': socket.getfqdn(),
                'DNS_DOMAIN': self._get_host_domain()
            })
    
    def _get_host_domain(self):
        """Get the host domain name."""
        fqdn = socket.getfqdn()
        parts = fqdn.split('.', 1)
        return parts[1] if len(parts) > 1 else ''