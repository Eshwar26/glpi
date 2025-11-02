#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic PCI Videos - Python Implementation
"""

import os
import re
import platform
from typing import Any, List, Dict, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_first_match
from GLPI.Agent.Tools.Generic import get_pci_devices, get_pci_device_vendor
from GLPI.Agent.Tools.Unix import get_x_authority_file


class Videos(InventoryModule):
    """PCI video cards inventory module."""
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "video"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        # Windows has dedicated module
        return platform.system() != 'Windows'
    
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
        """Get PCI video cards."""
        videos = []
        
        for device in get_pci_devices(**params):
            if not device.get('NAME'):
                continue
            if not re.search(r'graphics|vga|video|display|3D controller', device['NAME'], re.IGNORECASE):
                continue
            
            vendor_id, device_id = device['PCIID'].split(':')
            
            # Try to extract chipset and name
            chipset = None
            name = None
            manufacturer_match = re.match(r'^(.*)\s+\[(.*)\]$', device.get('MANUFACTURER', ''))
            if manufacturer_match:
                chipset, name = manufacturer_match.groups()
            
            vendor = get_pci_device_vendor(id=vendor_id, **params)
            if not chipset and vendor and vendor.get('devices', {}).get(device_id, {}).get('name'):
                device_name = vendor['devices'][device_id]['name']
                name_match = re.match(r'^(.*)\s+\[(.*)\]$', device_name)
                if name_match:
                    name, chipset = name_match.groups()
            
            # Get manufacturer from subsystem ID
            manufacturer = None
            if device.get('PCISUBSYSTEMID'):
                subsys_vendor_id = device['PCISUBSYSTEMID'].split(':')[0]
                subsys_vendor = get_pci_device_vendor(id=subsys_vendor_id, **params)
                if subsys_vendor:
                    manufacturer = subsys_vendor.get('name')
                    if manufacturer and name:
                        name = f"{manufacturer} {name}"
            
            video = {
                'PCIID': device['PCIID'],
                'PCISLOT': device.get('PCISLOT'),
                'CHIPSET': chipset or device['NAME'],
                'NAME': name or device.get('MANUFACTURER')
            }
            
            if device.get('MEMORY'):
                video['MEMORY'] = device['MEMORY']
            
            videos.append(video)
        
        # Try to catch resolution with standard X11 clients if only one card is detected
        if len(videos) == 1:
            xauth = None
            resolution = None
            
            if not os.environ.get('XAUTHORITY') and not params.get('file'):
                # Setup environment to be trusted by current running X server
                xauth = get_x_authority_file(**params)
                if xauth:
                    os.environ['XAUTHORITY'] = xauth
            
            if can_run('xrandr') or params.get('xrandr'):
                file_param = params.get('file', '')
                if params.get('xrandr'):
                    file_param += '.xrandr'
                
                result = get_first_match(
                    command='xrandr -d :0',
                    pattern=r'^Screen.*current (\d+) x (\d+),',
                    file=file_param if file_param else None,
                    **{k: v for k, v in params.items() if k != 'file'}
                )
                if result:
                    xres, yres = result if isinstance(result, tuple) else (result, None)
                    if xres and yres:
                        resolution = f'{xres}x{yres}'
            
            if not resolution and (can_run('xdpyinfo') or params.get('xdpyinfo')):
                file_param = params.get('file', '')
                if params.get('xdpyinfo'):
                    file_param += '.xdpyinfo'
                
                result = get_first_match(
                    command='xdpyinfo -d :0',
                    pattern=r'^\s+dimensions:\s+(\d+x\d+)\s+pixels',
                    file=file_param if file_param else None,
                    **{k: v for k, v in params.items() if k != 'file'}
                )
                if result:
                    resolution = result if isinstance(result, str) else result[0]
            
            if resolution:
                videos[0]['RESOLUTION'] = resolution
            
            # Cleanup environment
            if xauth and 'XAUTHORITY' in os.environ:
                del os.environ['XAUTHORITY']
        
        return videos
