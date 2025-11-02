#!/usr/bin/env python3
"""
GLPI Agent Task Inventory MacOS AntiVirus CrowdStrike - Python Implementation
"""

import re
from typing import Any, Optional, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines, first


COMMAND = '/Applications/Falcon.app/Contents/Resources/falconctl'


class CrowdStrike(InventoryModule):
    """CrowdStrike Falcon Sensor detection module for macOS."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run(COMMAND)
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        antivirus = CrowdStrike._get_crowdstrike(logger=logger)
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
    def _get_crowdstrike(**params) -> Optional[Dict[str, Any]]:
        """Get CrowdStrike Falcon information."""
        antivirus = {
            'COMPANY': 'CrowdStrike',
            'NAME': 'CrowdStrike Falcon Sensor',
            'ENABLED': 0,
        }
        
        lines = get_all_lines(
            command=f'{COMMAND} stats agent_info',
            **params
        )
        
        if lines:
            version_line = first(lambda line: 'version:' in line, lines)
            if version_line:
                match = re.match(r'^\s*version:\s*([0-9.]+[0-9]+)$', version_line)
                if match:
                    antivirus['VERSION'] = match.group(1)
            
            if first(lambda line: re.search(r'Sensor operational: true', line, re.IGNORECASE), lines):
                antivirus['ENABLED'] = 1
        
        return antivirus
