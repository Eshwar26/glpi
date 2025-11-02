#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux Inputs - Python Implementation
"""

import re
from typing import Any, List, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_read, get_all_lines


class Inputs(InventoryModule):
    """Linux input devices detection module."""
    
    category = "input"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_read('/proc/bus/input/devices')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        lines = get_all_lines(
            file='/proc/bus/input/devices',
            logger=logger
        )
        if not lines:
            return
        
        inputs = []
        device = {}
        in_device = False
        
        for line in lines:
            if re.match(r'^I: Bus=.*Vendor=(.*) Prod', line):
                in_device = True
                match = re.search(r'Vendor=([^\s]+)', line)
                if match:
                    device['vendor'] = match.group(1)
            elif re.match(r'^$', line):
                in_device = False
                if device.get('phys') and 'input' in device['phys']:
                    inputs.append({
                        'DESCRIPTION': device.get('name'),
                        'CAPTION': device.get('name'),
                        'TYPE': device.get('type'),
                    })
                device = {}
            elif in_device:
                if re.search(r'^P: Phys=.*(button).*', line, re.IGNORECASE):
                    device['phys'] = 'nodev'
                elif re.search(r'^P: Phys=.*(input).*', line, re.IGNORECASE):
                    device['phys'] = 'input'
                
                name_match = re.match(r'^N: Name="(.*)"', line, re.IGNORECASE)
                if name_match:
                    device['name'] = name_match.group(1)
                
                handler_match = re.match(r'^H: Handlers=(\w+)', line, re.IGNORECASE)
                if handler_match:
                    handler = handler_match.group(1)
                    if 'kbd' in handler:
                        device['type'] = 'Keyboard'
                    elif 'mouse' in handler:
                        device['type'] = 'Pointing'
                    else:
                        # Keyboard or Pointing
                        device['type'] = handler
        
        for input_device in inputs:
            if inventory:
                inventory.add_entry(
                    section='INPUTS',
                    entry=input_device
                )
