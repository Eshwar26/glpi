#!/usr/bin/env python3
"""
GLPI Agent Task Inventory AIX Videos - Python Implementation
"""

import re
from typing import Dict, Any, List

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run
from GLPI.Agent.Tools.AIX import get_adapters_from_lsdev


class Videos(InventoryModule):
    """AIX Videos inventory module."""
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "video"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('lsdev')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        videos = Videos._get_videos(logger=logger)
        
        for video in videos:
            if inventory:
                inventory.add_entry(
                    section='VIDEOS',
                    entry=video
                )
    
    @staticmethod
    def _get_videos(**params) -> List[Dict[str, Any]]:
        """Get video devices information."""
        adapters = get_adapters_from_lsdev(**params)
        
        videos = []
        for adapter in adapters:
            description = adapter.get('DESCRIPTION', '')
            if re.search(r'graphics|vga|video', description, re.IGNORECASE):
                videos.append({
                    'NAME': adapter.get('NAME'),
                })
        
        return videos
