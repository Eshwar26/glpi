#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux ARM Board - Python Implementation
"""

import re
from typing import Any, Optional, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_read, get_all_lines, trim_whitespace


class Board(InventoryModule):
    """ARM board information detection module."""
    
    category = "bios"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_read('/proc/cpuinfo')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        
        bios = Board._get_bios(logger=params.get('logger'))
        
        if bios and inventory:
            inventory.set_bios(bios)
    
    @staticmethod
    def _get_bios(**params) -> Optional[Dict[str, str]]:
        """Get BIOS information from board data."""
        bios = None
        
        board = params.get('board') or Board._get_board_from_proc(**params)
        
        if board:
            # List of well-known inventory values we can import
            # Search for cpuinfo value from the given list
            infos = {
                'MMODEL': ['hardware', 'model'],
                'MSN': ['revision'],
                'SSN': ['serial']
            }
            
            # Map found informations
            for key, info_keys in infos.items():
                for info in info_keys:
                    if board.get(info):
                        if not bios:
                            bios = {}
                        bios[key] = board[info]
                        break
        
        return bios
    
    @staticmethod
    def _get_board_from_proc(**params) -> Optional[Dict[str, str]]:
        """Parse board information from /proc/cpuinfo."""
        if 'file' not in params:
            params['file'] = '/proc/cpuinfo'
        
        lines = get_all_lines(**params)
        if not lines:
            return None
        
        infos = {}
        
        # Does the inverse of GLPI::Agent::Tools::Linux::getCPUsFromProc()
        for line in lines:
            match = re.match(r'^([^:]+\S) \s* : \s (.+)', line, re.VERBOSE)
            if match:
                infos[match.group(1).lower()] = trim_whitespace(match.group(2))
            elif re.match(r'^$', line):
                # Quit if not a cpu
                if not infos or not ('processor' in infos or 'cpu' in infos):
                    break
                infos = {}
        
        # Return last parsed section if it's a CPU section
        if infos and ('processor' in infos or 'cpu' in infos):
            return infos
        
        return None
