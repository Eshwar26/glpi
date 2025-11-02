#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Firewall Systemd - Python Implementation
"""

import re
from typing import Any

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines
from GLPI.Agent.Tools.Constants import STATUS_ON, STATUS_OFF


class Systemd(InventoryModule):
    """Systemd firewall inventory module."""
    
    run_me_if_these_checks_failed = ["GLPI.Agent.Task.Inventory.Generic.Firewall.Ufw"]
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('systemctl')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        firewall_status = Systemd._get_firewall_status(logger=logger)
        
        if inventory:
            inventory.add_entry(
                section='FIREWALL',
                entry={
                    'DESCRIPTION': 'firewalld',
                    'STATUS': firewall_status
                }
            )
    
    @staticmethod
    def _get_firewall_status(**params) -> str:
        """Get firewalld status via systemctl."""
        lines = get_all_lines(
            command='systemctl status firewalld.service',
            **params
        )
        
        # Multiline regexp to match for example:
        #   Loaded: loaded (/usr/lib/systemd/system/firewalld.service; enabled; vendor preset: enabled)
        #   Active: active (running) since Tue 2017-03-14 15:33:24 CET; 1h 16min ago
        # This permits to check if service is loaded, enabled and active
        full_text = '\n'.join(lines) if lines else ''
        
        pattern = r'^\s*Loaded: loaded [^;]+firewalld[^;]*; [^;]*;[^\n]*\n\s*Active: active \(running\)'
        if re.search(pattern, full_text, re.MULTILINE):
            return STATUS_ON
        else:
            return STATUS_OFF
