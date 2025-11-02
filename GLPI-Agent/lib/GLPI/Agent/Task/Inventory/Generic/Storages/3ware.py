#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Storages 3ware - Python Implementation

Tested on 2.6.* kernels

Cards tested:
- 8006-2LP
- 9500S-4LP
- 9550SXU-4LP
- 9550SXU-8LP
- 9650SE-2LP
- 9650SE-4LPML
- 9650SE-8LPML

AMCC/3ware CLI (version 2.00.0X.XXX)
"""

import platform
import re
from typing import Any, List, Dict, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_first_match, get_all_lines, get_canonical_manufacturer


class Ware3(InventoryModule):
    """3ware RAID controller inventory module."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('tw_cli')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        devices = []
        
        for card in Ware3._get_cards():
            for unit in Ware3._get_units(card):
                # Try to get unit's serial in order to compare it to what was found
                # in udev db. Works only on newer cards.
                # Allow us to associate a node to a drive: sda -> WD-WMANS1648590
                sn = get_first_match(
                    logger=logger,
                    command=f"tw_cli info {card['id']} {unit['id']} serial",
                    pattern=r'serial number\s=\s(\w+)'
                )
                
                for port in Ware3._get_ports(card, unit):
                    # Finally, getting drives' values
                    storage = Ware3._get_storage(card, port)
                    
                    if platform.system() == 'Linux':
                        if not devices:
                            from GLPI.Agent.Tools.Linux import get_devices_from_udev
                            devices = get_devices_from_udev(logger=logger)
                        
                        for device in devices:
                            # How does this work with multiple older cards
                            # where serial for units is not implemented?
                            # Need to be tested on a system with multiple 3ware cards.
                            if (device.get('SERIALNUMBER') == f'AMCC_{sn}' or
                                    device.get('MODEL') == f'Logical_Disk_{unit["index"]}'):
                                storage['NAME'] = device.get('NAME')
                    
                    if inventory:
                        inventory.add_entry(section='STORAGES', entry=storage)
    
    @staticmethod
    def _get_cards(**params) -> List[Dict[str, str]]:
        """Get list of 3ware cards."""
        lines = get_all_lines(command='tw_cli info', **params)
        if not lines:
            return []
        
        cards = []
        for line in lines:
            match = re.match(r'^(c\d+)\s+([\w-]+)', line)
            if match:
                cards.append({'id': match.group(1), 'model': match.group(2)})
        
        return cards
    
    @staticmethod
    def _get_units(card: Dict[str, str], **params) -> List[Dict[str, Any]]:
        """Get units for a card."""
        lines = get_all_lines(command=f"tw_cli info {card['id']}", **params)
        if not lines:
            return []
        
        units = []
        for line in lines:
            match = re.match(r'^(u(\d+))', line)
            if match:
                units.append({'id': match.group(1), 'index': int(match.group(2))})
        
        return units
    
    @staticmethod
    def _get_ports(card: Dict[str, str], unit: Dict[str, Any], **params) -> List[Dict[str, str]]:
        """Get ports for a unit."""
        lines = get_all_lines(command=f"tw_cli info {card['id']} {unit['id']}", **params)
        if not lines:
            return []
        
        ports = []
        for line in lines:
            match = re.search(r'(p\d+)', line)
            if match:
                ports.append({'id': match.group(1)})
        
        return ports
    
    @staticmethod
    def _get_storage(card: Dict[str, str], port: Dict[str, str], **params) -> Dict[str, Any]:
        """Get storage information for a port."""
        lines = get_all_lines(
            command=f"tw_cli info {card['id']} {port['id']} model serial capacity firmware",
            **params
        )
        if not lines:
            return {}
        
        storage = {}
        for line in lines:
            if re.match(r'Model\s=\s(.*)', line):
                match = re.match(r'Model\s=\s(.*)', line)
                storage['MODEL'] = match.group(1)
            elif re.match(r'Serial\s=\s(.*)', line):
                match = re.match(r'Serial\s=\s(.*)', line)
                storage['SERIALNUMBER'] = match.group(1)
            elif re.match(r'Capacity\s=\s(\S+)\sGB.*', line):
                match = re.match(r'Capacity\s=\s(\S+)\sGB.*', line)
                storage['DISKSIZE'] = int(1024 * float(match.group(1)))
            elif re.match(r'Firmware Version\s=\s(.*)', line):
                match = re.match(r'Firmware Version\s=\s(.*)', line)
                storage['FIRMWARE'] = match.group(1)
        
        if storage.get('MODEL'):
            storage['MANUFACTURER'] = get_canonical_manufacturer(storage['MODEL'])
        
        storage['TYPE'] = 'disk'
        
        # Getting description from card model, very basic and unreliable
        # Assuming only IDE drives can be plugged in 5xxx/6xxx cards and
        # SATA drives only to 7xxx/8xxx/9xxxx cards
        if re.match(r'^[56]', card['model']):
            storage['DESCRIPTION'] = 'IDE'
        elif re.match(r'^[789]', card['model']):
            storage['DESCRIPTION'] = 'SATA'
        
        return storage
