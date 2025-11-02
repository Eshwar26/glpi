#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux AntiVirus Defender - Python Implementation
"""

import json
import time
from typing import Any, Optional, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines


class Defender(InventoryModule):
    """Microsoft Defender detection module for Linux."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('mdatp')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        antivirus = Defender._get_ms_defender(logger=logger)
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
    def _get_ms_defender(**params) -> Optional[Dict[str, Any]]:
        """Get Microsoft Defender information."""
        if 'command' not in params:
            params['command'] = 'mdatp health --output json'
        
        antivirus = {
            'COMPANY': 'Microsoft',
            'NAME': 'Microsoft Defender',
            'ENABLED': 0,
            'UPTODATE': 0,
        }
        
        output = get_all_lines(**params)
        if not output:
            return None
        
        # Join all lines for JSON parsing
        output_str = ''.join(output) if isinstance(output, list) else output
        
        try:
            infos = json.loads(output_str)
        except json.JSONDecodeError:
            return None
        
        if not isinstance(infos, dict) or not infos.get('healthy'):
            return None
        
        if infos.get('appVersion'):
            antivirus['VERSION'] = infos['appVersion']
        
        if infos.get('definitionsVersion'):
            antivirus['BASE_VERSION'] = infos['definitionsVersion']
        
        if infos.get('definitionsStatus'):
            status_type = infos['definitionsStatus'].get('$type', '')
            antivirus['UPTODATE'] = 1 if status_type == 'upToDate' else 0
        
        if infos.get('realTimeProtectionEnabled') and infos['realTimeProtectionEnabled'].get('value') is not None:
            # Check if value is true (boolean true)
            antivirus['ENABLED'] = 1 if infos['realTimeProtectionEnabled']['value'] is True else 0
        
        if infos.get('productExpiration') and isinstance(infos['productExpiration'], (int, str)):
            try:
                expiration_ms = int(infos['productExpiration'])
                date_tuple = time.localtime(expiration_ms / 1000)
                antivirus['EXPIRATION'] = time.strftime('%Y-%m-%d', date_tuple)
            except (ValueError, OSError):
                pass
        
        if infos.get('definitionsUpdated') and isinstance(infos['definitionsUpdated'], (int, str)):
            try:
                updated_ms = int(infos['definitionsUpdated'])
                date_tuple = time.localtime(updated_ms / 1000)
                antivirus['BASE_CREATION'] = time.strftime('%Y-%m-%d', date_tuple)
            except (ValueError, OSError):
                pass
        
        return antivirus
