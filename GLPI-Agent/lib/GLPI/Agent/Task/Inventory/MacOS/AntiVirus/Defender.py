#!/usr/bin/env python3
"""
GLPI Agent Task Inventory MacOS AntiVirus Defender - Python Implementation
"""

import json
from datetime import datetime
from typing import Any, Optional, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines


class Defender(InventoryModule):
    """Microsoft Defender for Endpoint detection module for macOS."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('/usr/local/bin/mdatp')
    
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
                version_info = f" v{antivirus['VERSION']}" if antivirus.get('VERSION') else ""
                logger.debug2(f"Added {antivirus['NAME']}{version_info}")
    
    @staticmethod
    def _get_ms_defender(**params) -> Optional[Dict[str, Any]]:
        """Get Microsoft Defender information."""
        if 'command' not in params:
            params['command'] = '/usr/local/bin/mdatp health --output json'
        
        antivirus = {
            'COMPANY': 'Microsoft',
            'NAME': 'Microsoft Defender',
            'ENABLED': 0,
            'UPTODATE': 0,
        }
        
        # Support file case for unittests if basefile is provided
        basefile = params.get('basefile')
        if basefile:
            params['file'] = f"{basefile}.json"
        
        output = get_all_lines(**params)
        if not output:
            return None
        
        # Join lines if it's a list
        if isinstance(output, list):
            output = ''.join(output)
        
        try:
            infos = json.loads(output)
        except (json.JSONDecodeError, ValueError):
            return None
        
        if not isinstance(infos, dict) or not infos.get('healthy'):
            return None
        
        if infos.get('appVersion'):
            antivirus['VERSION'] = infos['appVersion']
        
        if infos.get('definitionsVersion'):
            antivirus['BASE_VERSION'] = infos['definitionsVersion']
        
        if infos.get('definitionsStatus'):
            type_val = infos['definitionsStatus'].get('$type')
            antivirus['UPTODATE'] = 1 if type_val == 'upToDate' else 0
        
        if infos.get('realTimeProtectionEnabled'):
            value = infos['realTimeProtectionEnabled'].get('value')
            # Check for JSON true boolean value
            antivirus['ENABLED'] = 1 if value is True else 0
        
        # Handle productExpiration timestamp
        if infos.get('productExpiration') and str(infos['productExpiration']).isdigit():
            try:
                timestamp = int(infos['productExpiration']) / 1000
                dt = datetime.fromtimestamp(timestamp)
                antivirus['EXPIRATION'] = dt.strftime('%Y-%m-%d')
            except (ValueError, OSError):
                pass
        
        # Handle definitionsUpdated timestamp
        if infos.get('definitionsUpdated') and str(infos['definitionsUpdated']).isdigit():
            try:
                timestamp = int(infos['definitionsUpdated']) / 1000
                dt = datetime.fromtimestamp(timestamp)
                antivirus['BASE_CREATION'] = dt.strftime('%Y-%m-%d')
            except (ValueError, OSError):
                pass
        
        return antivirus
