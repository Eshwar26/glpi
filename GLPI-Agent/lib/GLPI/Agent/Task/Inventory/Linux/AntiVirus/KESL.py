#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux AntiVirus KESL - Python Implementation
"""

import re
from typing import Any, Optional, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_first_line, get_all_lines


class KESL(InventoryModule):
    """Kaspersky Endpoint Security for Linux detection module."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('kesl-control')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        antivirus = KESL._get_kesl_info(logger=logger)
        if antivirus:
            if inventory:
                inventory.add_entry(
                    section='ANTIVIRUS',
                    entry=antivirus
                )
            
            if logger:
                version_str = f" v{antivirus['VERSION']}" if antivirus.get('VERSION') else ""
                enabled_str = " [ENABLED]" if antivirus.get('ENABLED') else " [DISABLED]"
                expiration_str = f" Expires: {antivirus['EXPIRATION']}" if antivirus.get('EXPIRATION') else ""
                logger.debug2(f"Added {antivirus['NAME']}{version_str}{enabled_str}{expiration_str}")
    
    @staticmethod
    def _get_kesl_info(**params) -> Optional[Dict[str, Any]]:
        """Get Kaspersky Endpoint Security for Linux information."""
        av = {
            'NAME': 'Kaspersky Endpoint Security for Linux',
            'COMPANY': 'Kaspersky Lab',
            'ENABLED': 0,
            'UPTODATE': 0,
        }
        
        service_status = get_first_line(
            file=params.get('ksel_active'),  # Only used by tests
            command='systemctl is-active kesl.service',
            **params
        )
        av['ENABLED'] = 1 if service_status and service_status == 'active' else 0
        
        app_info = get_all_lines(
            file=params.get('ksel_appinfo'),  # Only used by tests
            command='kesl-control --app-info',
            **params
        )
        
        if app_info:
            for line in app_info:
                if not av.get('VERSION'):
                    match = re.match(r'^Version:\s+([\d.]+)', line)
                    if match:
                        av['VERSION'] = match.group(1)
                        continue
                
                if not av.get('EXPIRATION'):
                    match = re.search(r'license expiration date:\s+([\d-]+)', line, re.IGNORECASE)
                    if match:
                        av['EXPIRATION'] = match.group(1)
                        continue
                
                if not av.get('BASE_VERSION'):
                    match = re.match(r'^Last release date of databases:\s+([\d-]+)', line)
                    if match:
                        av['BASE_VERSION'] = match.group(1)
                        continue
        
        return av
