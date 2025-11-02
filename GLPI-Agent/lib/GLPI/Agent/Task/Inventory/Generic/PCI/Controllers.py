#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic PCI Controllers - Python Implementation
"""

from typing import Any, List, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools.Generic import get_pci_devices, get_pci_device_vendor, get_pci_device_class


class Controllers(InventoryModule):
    """PCI controllers inventory module."""
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "controller"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return True
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        datadir = params.get('datadir')
        
        controllers = Controllers._get_controllers(logger=logger, datadir=datadir)
        
        for controller in controllers:
            if inventory:
                inventory.add_entry(
                    section='CONTROLLERS',
                    entry=controller
                )
    
    @staticmethod
    def _get_controllers(**params) -> List[Dict[str, Any]]:
        """Get PCI controllers."""
        controllers = []
        
        for device in get_pci_devices(**params):
            if not device.get('PCIID'):
                continue
            
            # Duplicate entry to avoid modifying it directly
            controller = {
                'PCICLASS': device.get('PCICLASS'),
                'NAME': device.get('NAME'),
                'MANUFACTURER': device.get('MANUFACTURER'),
                'REV': device.get('REV'),
                'PCISLOT': device.get('PCISLOT'),
            }
            
            if device.get('DRIVER'):
                controller['DRIVER'] = device['DRIVER']
            if device.get('PCISUBSYSTEMID'):
                controller['PCISUBSYSTEMID'] = device['PCISUBSYSTEMID']
            
            vendor_id, device_id = device['PCIID'].split(':')
            controller['VENDORID'] = vendor_id
            controller['PRODUCTID'] = device_id
            subdevice_id = device.get('PCISUBSYSTEMID')
            
            vendor = get_pci_device_vendor(id=vendor_id, **params)
            if vendor:
                controller['MANUFACTURER'] = vendor.get('name')
                
                if vendor.get('devices', {}).get(device_id):
                    entry = vendor['devices'][device_id]
                    controller['CAPTION'] = entry.get('name')
                    
                    if subdevice_id and entry.get('subdevices', {}).get(subdevice_id):
                        controller['NAME'] = entry['subdevices'][subdevice_id].get('name')
                    else:
                        controller['NAME'] = entry.get('name')
            
            if not device.get('PCICLASS'):
                continue
            
            # Extract class and subclass IDs
            import re
            match = re.match(r'^(\S\S)(\S\S)$', device['PCICLASS'], re.VERBOSE)
            if not match:
                continue
            
            class_id, subclass_id = match.groups()
            
            pci_class = get_pci_device_class(id=class_id, **params)
            if pci_class:
                if subclass_id and pci_class.get('subclasses', {}).get(subclass_id):
                    controller['TYPE'] = pci_class['subclasses'][subclass_id].get('name')
                else:
                    controller['TYPE'] = pci_class.get('name')
            
            controllers.append(controller)
        
        return controllers
