#!/usr/bin/env python3
"""
GLPI Agent Task Inventory HPUX MP - Python Implementation
"""

from typing import Any, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_first_match
from GLPI.Agent.Tools.Network import ip_address_pattern


class MP(InventoryModule):
    """HP-UX Management Processor (MP) network interface detection module."""
    
    category = "network"
    
    # TODO: driver, pcislot, virtualdev
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return (can_run('/opt/hpsmh/data/htdocs/comppage/getMPInfo.cgi') or
                can_run('/opt/sfm/bin/CIMUtil'))
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        ipaddress = None
        if can_run('/opt/hpsmh/data/htdocs/comppage/getMPInfo.cgi'):
            ipaddress = MP._parse_get_mp_info(logger=logger)
        else:
            ipaddress = MP._parse_cim_util(logger=logger)
        
        if inventory:
            inventory.add_entry(
                section='NETWORKS',
                entry={
                    'DESCRIPTION': 'Management Interface - HP MP',
                    'TYPE': 'Ethernet',
                    'MANAGEMENT': 'MP',
                    'IPADDRESS': ipaddress,
                }
            )
    
    @staticmethod
    def _parse_get_mp_info(**params) -> Optional[str]:
        """Parse getMPInfo.cgi output."""
        return get_first_match(
            command='/opt/hpsmh/data/htdocs/comppage/getMPInfo.cgi',
            pattern=rf'RIBLink = "https?://({ip_address_pattern})";',
            **params
        )
    
    @staticmethod
    def _parse_cim_util(**params) -> Optional[str]:
        """Parse CIMUtil output."""
        return get_first_match(
            command='/opt/sfm/bin/CIMUtil -e root/cimv2 HP_ManagementProcessor',
            pattern=rf'^IPAddress\s+:\s+({ip_address_pattern})',
            **params
        )
