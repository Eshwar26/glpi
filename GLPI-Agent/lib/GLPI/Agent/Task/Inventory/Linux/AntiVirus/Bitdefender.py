#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux AntiVirus Bitdefender - Python Implementation
"""

from typing import Any, Optional, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines


class Bitdefender(InventoryModule):
    """Bitdefender antivirus detection module for Linux."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('/opt/bitdefender-security-tools/bin/bduitool')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        antivirus = Bitdefender._get_bitdefender_info(logger=logger)
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
    def _get_bitdefender_info(**params) -> Optional[Dict[str, Any]]:
        """Get Bitdefender antivirus information."""
        if 'command' not in params:
            params['command'] = '/opt/bitdefender-security-tools/bin/bduitool get ps'
        
        output = get_all_lines(**params)
        if not output:
            return None
        
        av = {
            'NAME': 'Bitdefender Endpoint Security Tools (BEST) for Linux',
            'COMPANY': 'Bitdefender',
            'ENABLED': 0,
            'UPTODATE': 1,
        }
        
        for line in output:
            import re
            match = re.match(r'^(?:\s+-\s)?([^:]+):\s+(.+)$', line)
            if not match:
                continue
            
            key, value = match.groups()
            if key == 'Product version':
                av['VERSION'] = value
            elif key == 'Engines version':
                av['BASE_VERSION'] = value
            elif key == 'Antimalware status':
                av['ENABLED'] = 1 if value == 'On' else 0
            elif re.match(r'New (product update|security content) available', key):
                # Set "uptodate" to 0 if one of "new product update available" or "new security content available" is not "no"
                if value != 'no':
                    av['UPTODATE'] = 0
            elif key == 'Last security content update':
                date_match = re.match(r'^(\d{4}-\d+-\d+) at', value)
                if date_match:
                    av['BASE_CREATION'] = date_match.group(1)
        
        return av
