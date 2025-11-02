#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic PCI Videos Nvidia - Python Implementation
"""

import re
from typing import Any, Dict, List, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines
from GLPI.Agent.Tools.Generic import get_pci_device_vendor


class Nvidia(InventoryModule):
    """Nvidia video cards inventory module using nvidia-settings."""
    
    PCISLOT_RE = re.compile(r'^(?:([0-9a-f]+):)?([0-9a-f]{2}):([0-9a-f]{2})\.([0-9a-f]+)$', re.IGNORECASE)
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "video"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('nvidia-settings')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        videos = inventory.get_section('VIDEOS') or []
        
        for video in Nvidia._get_nvidia_videos(logger=logger):
            # Try to find matching existing video entry
            current = None
            for v in videos:
                if Nvidia._same_pci_slot(v.get('PCISLOT', ''), video.get('PCISLOT', '')):
                    current = v
                    break
            
            if current:
                if video.get('NAME') and not current.get('NAME'):
                    current['NAME'] = video['NAME']
                if video.get('MEMORY'):
                    current['MEMORY'] = video['MEMORY']
                if not current.get('CHIPSET'):
                    current['CHIPSET'] = video.get('CHIPSET')
                if video.get('RESOLUTION'):
                    current['RESOLUTION'] = video['RESOLUTION']
            else:
                if inventory:
                    inventory.add_entry(
                        section='VIDEOS',
                        entry=video
                    )
    
    @staticmethod
    def _same_pci_slot(first: str, second: str) -> bool:
        """Check if two PCI slots are the same."""
        first_match = Nvidia.PCISLOT_RE.match(first)
        second_match = Nvidia.PCISLOT_RE.match(second)
        
        if not first_match or not second_match:
            return False
        
        first_groups = first_match.groups()
        second_groups = second_match.groups()
        
        return (
            int(first_groups[0] or '0', 16) == int(second_groups[0] or '0', 16) and
            int(first_groups[1], 16) == int(second_groups[1], 16) and
            int(first_groups[2], 16) == int(second_groups[2], 16) and
            int(first_groups[3], 16) == int(second_groups[3], 16)
        )
    
    @staticmethod
    def _update_pci(hash_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update PCI slot format."""
        dom = hash_data.pop('PCIDOMAIN', None)
        bus = hash_data.pop('PCIBUS', None)
        dev = hash_data.pop('PCIDEVICE', None)
        func = hash_data.pop('PCIFUNC', None)
        
        if bus is not None and dev is not None and func is not None:
            hash_data['PCISLOT'] = f"{bus:02x}:{dev:02x}.{func:x}"
            if dom:
                hash_data['PCISLOT'] = f"{dom:04x}:{hash_data['PCISLOT']}"
        
        return hash_data
    
    @staticmethod
    def _get_nvidia_gpus(**params) -> Optional[Dict[int, Dict[str, str]]]:
        """Get list of Nvidia GPUs."""
        params_copy = dict(params)
        params_copy['command'] = 'nvidia-settings -t -c all -q gpus'
        
        # Support test cases
        if params.get('file') and params.get('gpus'):
            params_copy['file'] = params['file'] + '.gpus'
        
        gpus = {}
        
        for line in get_all_lines(**params_copy):
            match = re.match(r'^\s+\[(\d+)\]\s+\[(gpu:\d+)\]\s+\((.*)\)$', line)
            if match:
                num, name, info = match.groups()
                gpus[int(num)] = {
                    'NAME': name,
                    'INFO': info
                }
        
        return gpus
    
    @staticmethod
    def _get_nvidia_videos(**params) -> List[Dict[str, Any]]:
        """Get Nvidia video cards details."""
        videos = []
        
        gpus = Nvidia._get_nvidia_gpus(**params)
        if not gpus:
            return videos
        
        for num in sorted(gpus.keys()):
            gpu = gpus[num]['NAME']
            video = None
            xres = yres = None
            
            for line in get_all_lines(
                command=f'nvidia-settings -t -c :{num} -q all',
                **params
            ):
                # Screen position
                match = re.match(r'^\s+ScreenPosition: x=\d+, y=\d+, width=(\d+), height=(\d+)$', line)
                if match:
                    xres, yres = match.groups()
                
                # Start of attributes for this GPU
                elif re.match(rf'^Attributes queryable via .*:{num}\[{re.escape(gpu)}\]:', line):
                    video = {'CHIPSET': gpus[num]['INFO']}
                    if xres and yres:
                        video['RESOLUTION'] = f'{xres}x{yres}'
                    continue
                
                # Start of attributes for another entity - save current video
                elif re.match(r'^Attributes queryable via', line):
                    if video:
                        videos.append(Nvidia._update_pci(video))
                        video = None
                
                if not video:
                    continue
                
                # Parse video attributes
                match = re.match(r'^\s+TotalDedicatedGPUMemory:\s+(\d+)', line)
                if match:
                    video['MEMORY'] = match.group(1)
                    continue
                
                match = re.match(r'^\s+PCIDomain:\s+(\d+)', line)
                if match:
                    video['PCIDOMAIN'] = int(match.group(1))
                    continue
                
                match = re.match(r'^\s+PCIBus:\s+(\d+)', line)
                if match:
                    video['PCIBUS'] = int(match.group(1))
                    continue
                
                match = re.match(r'^\s+PCIDevice:\s+(\d+)', line)
                if match:
                    video['PCIDEVICE'] = int(match.group(1))
                    continue
                
                match = re.match(r'^\s+PCIFunc:\s+(\d+)', line)
                if match:
                    video['PCIFUNC'] = int(match.group(1))
                    continue
                
                match = re.match(r'^\s+PCIID:\s+(\S+)', line)
                if match:
                    pciid_parts = match.group(1).split(',')
                    vendor_id = f"{int(pciid_parts[0]):04x}"
                    device_id = f"{int(pciid_parts[1]):04x}"
                    video['PCIID'] = f"{vendor_id}:{device_id}"
                    
                    vendor = get_pci_device_vendor(id=vendor_id, logger=params.get('logger'))
                    if vendor and vendor.get('devices', {}).get(device_id, {}).get('name'):
                        chipset = (vendor.get('name', '') + ' ') if vendor.get('name') else ''
                        device_name = vendor['devices'][device_id]['name']
                        name_match = re.match(r'^(.*)\s+\[(.*)\]$', device_name)
                        if name_match:
                            video['CHIPSET'] = chipset + name_match.group(1)
                            chipset += name_match.group(2)
                        video['NAME'] = chipset
            
            if video:
                videos.append(Nvidia._update_pci(video))
        
        return videos
