#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux Videos - Python Implementation
"""

import re
from typing import Any, Optional, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, can_read, has_file, get_all_lines, ReadLink
from GLPI.Agent.Tools.Unix import get_processes


class Videos(InventoryModule):
    """Linux video devices detection module."""
    
    category = "video"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return True
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        videos = inventory.get_section('VIDEOS') if inventory else []
        # Assume videos was detected via pci scan
        if videos:
            return
        
        if logger:
            logger.debug("retrieving display information:")
        
        ddcprobe_data = None
        if can_run('ddcprobe'):
            ddcprobe_data = Videos._get_ddcprobe_data(
                command='ddcprobe',
                logger=logger
            )
            if logger:
                logger.debug_result(
                    action='running ddcprobe command',
                    data=ddcprobe_data
                )
        else:
            if logger:
                logger.debug_result(
                    action='running ddcprobe command',
                    status='command not available'
                )
        
        xorg_data = None
        
        # Find Xorg process
        xorg_pid = None
        processes = get_processes(
            namespace="same",
            logger=logger,
            filter=re.compile(r'^(?:/usr/bin|/usr/X11R6/bin|/etc/X11|/usr/libexec)/X')
        )
        if processes:
            xorg_pid = processes[0].get('PID')
        
        if xorg_pid:
            fd = 0
            read = {}
            while can_read(f"/proc/{xorg_pid}/fd/{fd}"):
                link = ReadLink(f"/proc/{xorg_pid}/fd/{fd}")
                fd += 1
                if not link or not link.endswith('.log'):
                    continue
                if link in read:
                    continue
                if has_file(link):
                    xorg_data = Videos._parse_xorg_fd(file=link)
                    if logger:
                        logger.debug_result(
                            action=f"reading {link} Xorg log file",
                            data=xorg_data
                        )
                    if xorg_data:
                        break
                    read[link] = True
                else:
                    if logger:
                        logger.debug_result(
                            action=f"reading {link} Xorg log file",
                            status=f"non-readable link {link}"
                        )
        else:
            if logger:
                logger.debug_result(
                    action='reading Xorg log file',
                    status='unable to get Xorg PID'
                )
        
        if not xorg_data and not ddcprobe_data:
            return
        
        video = {
            'CHIPSET': (xorg_data.get('product') if xorg_data else None) or (ddcprobe_data.get('product') if ddcprobe_data else None),
            'MEMORY': (xorg_data.get('memory') if xorg_data else None) or (ddcprobe_data.get('memory') if ddcprobe_data else None),
            'NAME': (xorg_data.get('name') if xorg_data else None) or (ddcprobe_data.get('oem') if ddcprobe_data else None),
            'RESOLUTION': (xorg_data.get('resolution') if xorg_data else None) or (ddcprobe_data.get('dtiming') if ddcprobe_data else None),
            'PCISLOT': xorg_data.get('pcislot') if xorg_data else None,
            'PCIID': xorg_data.get('pciid') if xorg_data else None,
        }
        
        if video.get('MEMORY'):
            memory = video['MEMORY']
            if isinstance(memory, str) and memory.lower().endswith('kb'):
                try:
                    video['MEMORY'] = int(int(memory[:-2]) / 1024)
                except (ValueError, TypeError):
                    pass
        
        if video.get('RESOLUTION'):
            video['RESOLUTION'] = re.sub(r'@.*', '', video['RESOLUTION'])
        
        if inventory:
            inventory.add_entry(
                section='VIDEOS',
                entry=video
            )
    
    @staticmethod
    def _get_ddcprobe_data(**params) -> Optional[Dict[str, str]]:
        """Parse ddcprobe output."""
        lines = get_all_lines(**params)
        if not lines:
            return None
        
        data = {}
        for line in lines:
            # Remove control and non-ASCII characters
            line = re.sub(r'[^\x20-\x7E]', '', line)
            match = re.match(r'^(\S+):\s+(.*)', line)
            if match:
                data[match.group(1)] = match.group(2)
        
        return data
    
    @staticmethod
    def _parse_xorg_fd(**params) -> Optional[Dict[str, str]]:
        """Parse Xorg log file."""
        lines = get_all_lines(**params)
        if not lines:
            return None
        
        data = {}
        for line in lines:
            modeline_match = re.search(r'Modeline\s"(\S+?)"', line)
            if modeline_match and not data.get('resolution'):
                data['resolution'] = modeline_match.group(1)
            
            intel_match = re.search(r'Integrated Graphics Chipset:\s+(.*)', line)
            if intel_match:
                # Intel
                data['name'] = intel_match.group(1)
            
            virtual_match = re.search(r'Virtual screen size determined to be (\d+)\s*x\s*(\d+)', line)
            if virtual_match:
                # Nvidia
                data['resolution'] = f"{virtual_match.group(1)}x{virtual_match.group(2)}"
            
            nvidia_match = re.search(r'NVIDIA GPU\s*(.*?)\s*at', line)
            if nvidia_match:
                data['name'] = nvidia_match.group(1)
            
            vesa_oem_match = re.search(r'VESA VBE OEM:\s*(.*)', line)
            if vesa_oem_match:
                data['name'] = vesa_oem_match.group(1)
            
            vesa_product_match = re.search(r'VESA VBE OEM Product:\s*(.*)', line)
            if vesa_product_match:
                data['product'] = vesa_product_match.group(1)
            
            memory_match = re.search(r'(?:VESA VBE Total Mem| Memory): (\d+)\s*(\w+)', line, re.IGNORECASE)
            if memory_match:
                data['memory'] = memory_match.group(1) + memory_match.group(2)[:2]
            
            radeon_match = re.search(r'RADEON\(0\): Chipset: "(.*?)"', line, re.IGNORECASE)
            if radeon_match:
                # ATI /Radeon
                data['name'] = radeon_match.group(1)
            
            vesa_size_match = re.search(r'Virtual size is (\S+)', line, re.IGNORECASE)
            if vesa_size_match:
                # VESA / XFree86
                data['resolution'] = vesa_size_match.group(1)
            
            pci_match = re.search(
                r'PCI: \* \( (?:\d+:)? (\d+) : (\d+) : (\d+) \) \s (\w{4}:\w{4}:\w{4}:\w{4})?',
                line,
                re.VERBOSE
            )
            if pci_match:
                bus, dev, func = pci_match.group(1), pci_match.group(2), pci_match.group(3)
                data['pcislot'] = f"{int(bus):02d}:{int(dev):02d}.{int(func)}"
                if pci_match.group(4):
                    data['pciid'] = pci_match.group(4)
            
            nouveau_match = re.search(r'NOUVEAU\(0\): Chipset: "(.*)"', line)
            if nouveau_match:
                # Nouveau
                data['product'] = nouveau_match.group(1)
        
        return data
