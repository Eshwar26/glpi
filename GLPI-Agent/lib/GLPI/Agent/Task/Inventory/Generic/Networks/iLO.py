#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Networks iLO - Python Implementation
"""

import re
import platform
from typing import Any, Dict, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines
from GLPI.Agent.Tools.Network import get_subnet_address, ip_address_pattern


class iLO(InventoryModule):
    """HP iLO management interface inventory module."""
    
    run_me_if_these_checks_failed = ['GLPI.Agent.Task.Inventory.Generic.Ipmi.Lan']
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        if platform.system() == 'Windows':
            return can_run(r"C:\Program Files\HP\hponcfg\hponcfg.exe")
        else:
            return can_run('hponcfg')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        command = (
            r'"c:\Program Files\HP\hponcfg\hponcfg" /a /w output.txt >nul 2>&1 && type output.txt'
            if platform.system() == 'Windows'
            else 'hponcfg -aw -'
        )
        
        entry = iLO._parse_hponcfg(logger=logger, command=command)
        
        if inventory:
            inventory.add_entry(
                section='NETWORKS',
                entry=entry
            )
    
    @staticmethod
    def _parse_hponcfg(**params) -> Dict[str, Any]:
        """Parse hponcfg output."""
        lines = get_all_lines(**params)
        if not lines:
            return {}
        
        interface = {
            'DESCRIPTION': 'Management Interface - HP iLO',
            'TYPE': 'ethernet',
            'MANAGEMENT': 'iLO',
            'STATUS': 'Down',
        }
        
        logger = params.get('logger')
        
        for line in lines:
            # IP Address
            match = re.search(rf'<IP_ADDRESS VALUE="({ip_address_pattern()})" ?/>', line)
            if match:
                ip = match.group(1)
                if ip != '0.0.0.0':
                    interface['IPADDRESS'] = ip
            
            # Subnet Mask
            match = re.search(rf'<SUBNET_MASK VALUE="({ip_address_pattern()})" ?/>', line)
            if match:
                interface['IPMASK'] = match.group(1)
            
            # Gateway
            match = re.search(rf'<GATEWAY_IP_ADDRESS VALUE="({ip_address_pattern()})"/>', line)
            if match:
                interface['IPGATEWAY'] = match.group(1)
            
            # NIC Speed
            match = re.search(r'<NIC_SPEED VALUE="([0-9]+)" ?/>', line)
            if match:
                interface['SPEED'] = match.group(1)
            
            # Enable NIC
            if re.search(r'<ENABLE_NIC VALUE="Y" ?/>', line):
                interface['STATUS'] = 'Up'
            
            # Error detection
            if 'not found' in line:
                if logger:
                    logger.error(f"error in hponcfg output: {line.strip()}")
        
        if interface.get('IPADDRESS'):
            interface['IPSUBNET'] = get_subnet_address(
                interface['IPADDRESS'],
                interface.get('IPMASK')
            )
        
        return interface
