#!/usr/bin/env python3
"""
GLPI Agent Task Inventory MacOS AntiVirus Cortex - Python Implementation
"""

from typing import Any, Optional, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_first_match, empty


COMMAND = '/Library/Application Support/PaloAltoNetworks/Traps/bin/cytool'


class Cortex(InventoryModule):
    """Palo Alto Networks Cortex XDR detection module for macOS."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run(COMMAND)
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        antivirus = Cortex._get_cortex(logger=logger)
        if antivirus:
            if inventory:
                inventory.add_entry(
                    section='ANTIVIRUS',
                    entry=antivirus
                )
            
            if logger:
                version_info = f" v{antivirus['VERSION']}" if antivirus.get('VERSION') else ""
                logger.debug2(f"Added {antivirus['NAME']}{version_info}")
    
    @staticmethod
    def _get_cortex(**params) -> Optional[Dict[str, Any]]:
        """Get Cortex XDR information."""
        antivirus = {
            'COMPANY': 'Palo Alto Networks',
            'NAME': 'Cortex XDR',
            'ENABLED': 0,
        }
        
        # Support file case for unittests if basefile is provided
        basefile = params.get('basefile')
        if empty(basefile):
            params['command'] = f'"{COMMAND}" info'
        else:
            params['file'] = f"{basefile}-info"
        
        version = get_first_match(
            pattern=r'^Cortex XDR .* ([0-9.]+)$',
            **params
        )
        if version:
            antivirus['VERSION'] = version
        
        # Support file case for unittests if basefile is provided
        if empty(basefile):
            params['command'] = f'"{COMMAND}" info query'
        else:
            params['file'] = f"{basefile}-info-query"
        
        base_version = get_first_match(
            pattern=r'^Content Version:\s+(\S+)$',
            **params
        )
        if base_version:
            antivirus['BASE_VERSION'] = base_version
        
        # Support file case for unittests if basefile is provided
        if empty(basefile):
            params['command'] = f'"{COMMAND}" runtime query'
        else:
            params['file'] = f"{basefile}-runtime-query"
        
        status = get_first_match(
            pattern=r'^\s*pmd\s+\S+\s+\S+\s+(\S+)\s',
            **params
        )
        if status and status.lower() == 'running':
            antivirus['ENABLED'] = 1
        
        return antivirus
