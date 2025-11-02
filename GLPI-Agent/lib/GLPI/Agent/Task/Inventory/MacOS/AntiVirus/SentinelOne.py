#!/usr/bin/env python3
"""
GLPI Agent Task Inventory MacOS AntiVirus SentinelOne - Python Implementation
"""

import re
from typing import Any, Optional, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_first_match, get_all_lines, first, empty


COMMAND = '/Library/Sentinel/sentinel-agent.bundle/Contents/MacOS/sentinelctl'


class SentinelOne(InventoryModule):
    """SentinelOne EPP detection module for macOS."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run(COMMAND)
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        antivirus = SentinelOne._get_sentinelone(logger=logger)
        if antivirus:
            if inventory:
                inventory.add_entry(
                    section='ANTIVIRUS',
                    entry=antivirus
                )
            
            if logger:
                version_info = f" v{antivirus['VERSION']}" if antivirus.get('VERSION') else ""
                logger.debug2(f"Added {antivirus['NAME']} {version_info}")
    
    @staticmethod
    def _get_sentinelone(**params) -> Optional[Dict[str, Any]]:
        """Get SentinelOne information."""
        antivirus = {
            'COMPANY': 'Sentinel Labs Inc.',
            'NAME': 'SentinelOne EPP',
            'ENABLED': 0,
        }
        
        # Support file case for unittests if basefile is provided
        basefile = params.get('basefile')
        if empty(basefile):
            params['command'] = f'"{COMMAND}" version'
        else:
            params['file'] = f"{basefile}-version"
        
        version = get_first_match(
            pattern=r'^SentinelOne.* ([0-9.]+)$',
            **params
        )
        if version:
            antivirus['VERSION'] = version
        
        # Support file case for unittests if basefile is provided
        if empty(basefile):
            params['command'] = f'"{COMMAND}" status'
        else:
            params['file'] = f"{basefile}-status"
        
        lines = get_all_lines(**params)
        if lines:
            if first(lambda line: re.match(r'^\s+Protection:\s+enabled$', line, re.IGNORECASE), lines):
                antivirus['ENABLED'] = 1
        
        return antivirus
