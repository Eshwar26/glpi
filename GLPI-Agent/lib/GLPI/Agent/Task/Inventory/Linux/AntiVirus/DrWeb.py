#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux AntiVirus DrWeb - Python Implementation
"""

import re
from typing import Any, Optional, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_first_line, get_all_lines, get_first_match, month


class DrWeb(InventoryModule):
    """Dr.Web antivirus detection module for Linux."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('drweb-ctl')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        antivirus = DrWeb._get_drweb_info(logger=logger)
        if antivirus:
            if inventory:
                inventory.add_entry(
                    section='ANTIVIRUS',
                    entry=antivirus
                )
            
            if logger:
                version_str = f" v{antivirus['VERSION']}" if antivirus.get('VERSION') else ""
                enabled_str = " [ENABLED]" if antivirus.get('ENABLED') else " [DISABLED]"
                logger.debug2(f"Added {antivirus['NAME']}{version_str}{enabled_str}")
    
    @staticmethod
    def _get_drweb_info(**params) -> Optional[Dict[str, Any]]:
        """Get Dr.Web antivirus information."""
        av = {
            'NAME': 'Dr.Web',
            'COMPANY': 'Doctor Web',
            'ENABLED': 0,
            'UPTODATE': 0,
        }
        
        version_output = get_first_line(
            file=params.get('drweb_version'),  # Only used by tests
            command='drweb-ctl --version',
            **params
        )
        
        if version_output:
            match = re.search(r'drweb-ctl\s+([\d.]+)', version_output)
            if match:
                av['VERSION'] = match.group(1)
        
        service_status = get_first_line(
            file=params.get('drweb_active'),  # Only used by tests
            command='systemctl is-active drweb-configd.service',
            **params
        )
        av['ENABLED'] = 1 if service_status and service_status == 'active' else 0
        
        baseinfo = get_all_lines(
            file=params.get('drweb_baseinfo'),  # Only used by tests
            command='drweb-ctl baseinfo',
            **params
        )
        
        if baseinfo:
            for line in baseinfo:
                match = re.match(r'^Virus database timestamp:\s+(\S+)', line)
                if match:
                    av['BASE_VERSION'] = match.group(1)
        
        expiration = get_first_match(
            file=params.get('drweb_license'),  # Only used by tests
            command='drweb-ctl license',
            pattern=r'expires (\d+-\w+-\d+)',
            **params
        )
        if expiration:
            match = re.match(r'^(\d+)-(\w+)-(\d+)$', expiration)
            if match:
                year, month_str, day = match.groups()
                m = month(month_str)
                if m:
                    av['EXPIRATION'] = f"{year}-{m:02d}-{int(day):02d}"
        
        return av
