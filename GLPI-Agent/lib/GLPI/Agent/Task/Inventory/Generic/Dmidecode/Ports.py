#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Dmidecode Ports - Python Implementation
"""

from typing import Any, Dict, List, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools.Generic import get_dmidecode_infos


class Ports(InventoryModule):
    """Dmidecode ports inventory module."""
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "port"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return True
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        ports = Ports._get_ports(logger=logger)
        
        if not ports:
            return
        
        for port in ports:
            if inventory:
                inventory.add_entry(
                    section='PORTS',
                    entry=port
                )
    
    @staticmethod
    def _get_ports(**params) -> Optional[List[Dict[str, Optional[str]]]]:
        """Get ports from dmidecode."""
        infos = get_dmidecode_infos(**params)
        
        if not infos or not infos.get(8):
            return None
        
        ports = []
        for info in infos[8]:
            port = {
                'CAPTION': (info.get('External Reference Designator') or 
                          info.get('External Connector Type') or 
                          info.get('External Designator')),
                'DESCRIPTION': (info.get('Internal Connector Type') or 
                              info.get('External Designator') or 
                              info.get('Internal Designator') or 
                              info.get('External Connector Type')),
                'NAME': (info.get('Internal Reference Designator') or 
                        info.get('External Reference Designator') or 
                        info.get('Internal Designator') or 
                        info.get('External Designator')),
                'TYPE': info.get('Port Type') or info.get('External Connector Type'),
            }
            ports.append(port)
        
        return ports
