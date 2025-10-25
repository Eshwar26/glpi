"""
GLPI Agent Task Inventory Provider Module

Provides information about the GLPI Agent itself.
"""

import os
import sys
import platform


class Provider:
    """Provider inventory module"""
    
    category = "provider"
    
    # Agent program name (should be set by main agent)
    PROGRAM = None
    
    @staticmethod
    def is_enabled() -> bool:
        """Check if module is enabled"""
        return True
    
    @staticmethod
    def do_inventory(inventory=None, logger=None, config=None, **params) -> None:
        """
        Execute the inventory.
        
        Args:
            inventory: Inventory instance
            logger: Logger instance
            config=None, **params
        """
        if not inventory:
            return
        
        # Get program name
        program = Provider.PROGRAM or sys.argv[0]
        if program:
            program = os.path.basename(program)
        
        # Get agent version
        try:
            from GLPI.Agent.Version import VERSION
            version = VERSION
        except ImportError:
            version = "unknown"
        
        # Determine execution mode
        if config:
            if config.get('daemon') or config.get('service'):
                mode = 'Service' if platform.system() == 'Windows' else 'Daemon'
            else:
                mode = 'Task'
        else:
            mode = 'Unknown'
        
        inventory.set_provider({
            'NAME': program or 'glpi-agent',
            'VERSION': version,
            'COMMENTS': f'GLPI Agent running in {mode} mode'
        })
