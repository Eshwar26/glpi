# glpi_agent/task/inventory/generic/environment.py

import platform
import os

from glpi_agent.task.inventory.module import InventoryModule
from glpi_agent.tools import get_all_lines


class Environment(InventoryModule):
    """Generic Environment inventory module."""
    
    @staticmethod
    def category():
        return "environment"
    
    def is_enabled(self, **params):
        # We use WMI for Windows because of charset issue
        return platform.system() != 'Windows'
    
    def do_inventory(self, **params):
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        env = {}
        if inventory.get_remote():
            for line in get_all_lines(
                command='env',
                logger=logger
            ):
                import re
                match = re.match(r'^(\w+)=(.*)$', line)
                if not match:
                    continue
                key, value = match.groups()
                if key == '_' or value is None:
                    continue
                env[key] = value
        else:
            env = os.environ.copy()
        
        for key in sorted(env.keys()):
            inventory.add_entry(
                section='ENVS',
                entry={
                    'KEY': key,
                    'VAL': env[key]
                }
            )