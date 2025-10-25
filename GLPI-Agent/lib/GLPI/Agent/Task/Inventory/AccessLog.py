"""
GLPI Agent Task Inventory AccessLog Module

Records access log timestamp for inventory.
"""

import time
from datetime import datetime


class AccessLog:
    """Access log inventory module"""
    
    category = "accesslog"
    
    @staticmethod
    def is_enabled() -> bool:
        """Check if module is enabled"""
        return True
    
    @staticmethod
    def do_inventory(inventory=None, **params) -> None:
        """
        Execute the inventory.
        
        Args:
            inventory: Inventory instance
            **params: Additional parameters
        """
        if not inventory:
            return
        
        # Get formatted local time
        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        inventory.set_access_log({
            'LOGDATE': date
        })
