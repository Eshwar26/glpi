#!/usr/bin/env python3
"""
GLPI Agent Task Inventory BSD Storages - Python Implementation
"""

import re
from typing import Any, List, Dict, Optional
import xml.etree.ElementTree as ET

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines, get_first_match


class Storages(InventoryModule):
    """BSD Storages inventory module."""
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "storage"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('sysctl')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        storages = Storages._get_storages(logger=logger)
        
        for storage in storages:
            if inventory:
                inventory.add_entry(
                    section='STORAGES',
                    entry=storage
                )
    
    @staticmethod
    def _get_storages(**params) -> List[Dict[str, Any]]:
        """Get storage devices."""
        logger = params.get('logger')
        
        command = 'sysctl kern.geom.confxml'
        lines = get_all_lines(command=command, logger=logger)
        
        if not lines:
            return []
        
        # Join lines and remove the sysctl prefix
        xml_str = ''.join(lines)
        xml_str = re.sub(r'^kern\.geom\.confxml:', '', xml_str)
        
        storages = []
        
        try:
            # Parse XML
            root = ET.fromstring(xml_str)
            
            # Find mesh/class elements
            for class_elem in root.findall('.//class'):
                name = class_elem.get('name') or class_elem.findtext('name', '')
                if name != 'DISK':
                    continue
                
                for geom in class_elem.findall('geom'):
                    device = {}
                    
                    # Get device name
                    geom_name = geom.get('name') or geom.findtext('name')
                    if geom_name:
                        device['NAME'] = geom_name
                    
                    # Get provider information
                    provider = geom.find('provider')
                    if provider is not None:
                        # Get description from config
                        config = provider.find('config')
                        if config is not None:
                            descr = config.findtext('descr')
                            if descr:
                                device['DESCRIPTION'] = descr
                        
                        # Get media size
                        mediasize = provider.findtext('mediasize')
                        if mediasize:
                            device['DISKSIZE'] = int(mediasize)
                    
                    # Determine device type
                    if 'NAME' in device:
                        device['TYPE'] = Storages._retrieve_device_type_from_name(device['NAME'])
                    
                    storages.append(device)
        
        except ET.ParseError:
            # If XML parsing fails, return empty list
            pass
        
        # Unittest support
        file_param = params.get('dmesgFile') or params.get('file')
        if file_param:
            params['file'] = file_param
        
        # Extract additional data from dmesg
        Storages._extract_data_from_dmesg(storages=storages, **params)
        
        return storages
    
    @staticmethod
    def _retrieve_device_type_from_name(name: Optional[str]) -> str:
        """Determine device type from name."""
        if not name:
            return 'unknown'
        
        if re.match(r'^da', name):
            return 'disk'
        elif re.match(r'^ada', name):
            return 'disk'
        elif re.match(r'^cd', name):
            return 'cdrom'
        else:
            return 'unknown'
    
    @staticmethod
    def _extract_data_from_dmesg(**params):
        """Extract additional storage data from dmesg."""
        storages = params.get('storages', [])
        
        dmesg_lines = get_all_lines(command='dmesg', **params)
        if not dmesg_lines:
            return
        
        # Join lines for easier searching
        dmesg_str = '\n'.join(dmesg_lines)
        
        for storage in storages:
            name = storage.get('NAME')
            if not name:
                continue
            
            # Extract model
            model = get_first_match(
                string=dmesg_str,
                pattern=rf'^\Q{name}\E.*<(.*)>'
            )
            if model:
                storage['MODEL'] = model
            
            # Extract description
            desc = get_first_match(
                string=dmesg_str,
                pattern=rf'^\Q{name}\E: (.*<.*>.*)$'
            )
            if desc:
                storage['DESCRIPTION'] = desc
            
            # Extract serial number
            serial = get_first_match(
                string=dmesg_str,
                pattern=rf'^\Q{name}\E: Serial Number (.*)$'
            )
            if serial:
                storage['SERIALNUMBER'] = serial
            
            # Extract manufacturer from model
            if storage.get('MODEL'):
                match = re.match(
                    r'^(SGI|SONY|WDC|ASUS|LG|TEAC|SAMSUNG|PHILIPS|PIONEER|MAXTOR|'
                    r'PLEXTOR|SEAGATE|IBM|SUN|SGI|DEC|FUJITSU|TOSHIBA|YAMAHA|'
                    r'HITACHI|VERITAS)\s*',
                    storage['MODEL'],
                    re.IGNORECASE
                )
                if match:
                    storage['MANUFACTURER'] = match.group(1)
                    storage['MODEL'] = re.sub(
                        r'^(SGI|SONY|WDC|ASUS|LG|TEAC|SAMSUNG|PHILIPS|PIONEER|MAXTOR|'
                        r'PLEXTOR|SEAGATE|IBM|SUN|SGI|DEC|FUJITSU|TOSHIBA|YAMAHA|'
                        r'HITACHI|VERITAS)\s*',
                        '',
                        storage['MODEL'],
                        flags=re.IGNORECASE
                    )
                
                # Clean up the model
                storage['MODEL'] = re.sub(r'^(\s|,)*', '', storage['MODEL'])
                storage['MODEL'] = re.sub(r'(\s|,)*$', '', storage['MODEL'])
