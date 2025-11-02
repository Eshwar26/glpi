#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux AntiVirus Sentinelone - Python Implementation
"""

import re
from typing import Any, Optional, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines


class Sentinelone(InventoryModule):
    """SentinelOne detection module for Linux."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('/opt/sentinelone/bin/sentinelctl')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        antivirus = Sentinelone._get_sentinelone_info(logger=logger)
        if antivirus:
            if inventory:
                inventory.add_entry(
                    section='ANTIVIRUS',
                    entry=antivirus
                )
            
            if logger:
                version_str = f" v{antivirus['VERSION']}" if antivirus.get('VERSION') else ""
                logger.debug2(f"Added {antivirus['NAME']}{version_str}")
    
    @staticmethod
    def _get_sentinelone_info(**params) -> Optional[Dict[str, Any]]:
        """Get SentinelOne information."""
        cmd = '/opt/sentinelone/bin/sentinelctl'
        
        output = get_all_lines(
            command=f'{cmd} version && {cmd} engines status && {cmd} control status && {cmd} management status',
            **params
        )
        if not output:
            return None
        
        av = {
            'NAME': 'SentinelAgent',
            'COMPANY': 'SentinelOne',
            'ENABLED': 0,
            'UPTODATE': 0,
        }
        
        for line in output:
            # Match pattern: "key: value" or "key  value" (with 2+ spaces)
            match = re.match(r'(.+)(?:: |(?<!\s)\s{2,})(.*)', line)
            if not match:
                continue
            
            key, value = match.groups()
            if key == 'Agent version':
                av['VERSION'] = value
            elif key == 'DFI library version':
                av['BASE_VERSION'] = value
            elif key == 'Agent state':
                av['ENABLED'] = 1 if value == 'Enabled' else 0
            elif key == 'Connectivity':
                # SentinelAgent does not directly report "uptodate" status but we can assume it is updated if the cloud connectivity is working.
                av['UPTODATE'] = 1 if value == 'On' else 0
        
        return av
