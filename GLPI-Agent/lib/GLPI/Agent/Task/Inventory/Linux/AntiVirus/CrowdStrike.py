#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux AntiVirus CrowdStrike - Python Implementation
"""

from typing import Any, Optional, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_first_match


class CrowdStrike(InventoryModule):
    """CrowdStrike Falcon Sensor detection module for Linux."""
    
    FALCONCTL = '/opt/CrowdStrike/falconctl'
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run(CrowdStrike.FALCONCTL)
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        antivirus = CrowdStrike._get_crowdstrike_info(logger=logger)
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
    def _get_crowdstrike_info(**params) -> Optional[Dict[str, Any]]:
        """Get CrowdStrike Falcon Sensor information."""
        av = {
            'NAME': 'CrowdStrike Falcon Sensor',
            'COMPANY': 'CrowdStrike',
            'ENABLED': 0,
        }
        
        version = get_first_match(
            pattern=r'version\s*=\s*([0-9.]+[0-9]+)',
            command=f'{CrowdStrike.FALCONCTL} -g --version',
            **params
        )
        
        if version:
            av['VERSION'] = version
            # Assume AV is enabled if we got version
            av['ENABLED'] = 1
        
        return av
