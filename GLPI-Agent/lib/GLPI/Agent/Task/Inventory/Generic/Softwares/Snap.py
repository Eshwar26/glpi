#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Softwares Snap - Python Implementation
"""

import os
import platform
import re
import time
from typing import Any, List, Dict, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_first_line, get_first_match, get_all_lines, has_folder, get_canonical_size


class Snap(InventoryModule):
    """Snap package inventory module."""
    
    MAPPING = {
        'name': 'NAME',
        'publisher': 'PUBLISHER',
        'summary': 'COMMENTS',
        'contact': 'HELPLINK',
    }
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        # Snap is not supported on AIX and the command has another usage
        if platform.system() == 'AIX' or not can_run('snap'):
            return False
        
        # Try to check if snapd is active/running
        if can_run('pgrep'):
            if can_run('systemctl') and get_first_line(command='pgrep -g 1 -x systemd'):
                status = get_first_line(command='systemctl is-active snapd')
                if status and re.search(r'inactive', status):
                    return False
            elif not get_first_line(command='pgrep -x snapd'):
                return False
        
        return True
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        # Don't try to contact snapd if said not available by "snap version"
        snapd = get_first_match(
            logger=logger,
            command='snap version',
            pattern=r'^snapd\s+(\S+)$',
        )
        if snapd and snapd == 'unavailable':
            return
        
        packages = Snap._get_packages_list(
            logger=logger,
            command='snap list --color never',
        )
        if not packages:
            return
        
        for snap in packages:
            rev = snap.pop('_REVISION', None)
            Snap._get_packages_info(
                logger=logger,
                snap=snap,
                command=f'snap info --color never --abs-time {snap["NAME"]}',
                file=f'/snap/{snap["NAME"]}/{rev}/meta/snap.yaml',
            )
            if inventory:
                inventory.add_entry(
                    section='SOFTWARES',
                    entry=snap
                )
    
    @staticmethod
    def _get_packages_list(**params) -> Optional[List[Dict[str, Any]]]:
        """Get list of Snap packages."""
        lines = get_all_lines(**params)
        if not lines:
            return None
        
        packages = []
        
        for line in lines:
            infos = line.split()
            if not infos:
                continue
            
            # Skip header
            if infos[0] == 'Name' and len(infos) > 1 and infos[1] == 'Version':
                continue
            
            # Skip base and snapd
            if len(infos) > 5 and re.match(r'^base|core|snapd$', infos[5]):
                continue
            
            snap = {
                'NAME': infos[0] if len(infos) > 0 else '',
                'VERSION': infos[1] if len(infos) > 1 else '',
                '_REVISION': infos[2] if len(infos) > 2 else '',
                'PUBLISHER': infos[4] if len(infos) > 4 else '',
                'FROM': 'snap'
            }
            
            folder = f"/snap/{snap['NAME']}"
            # Don't check install date during unittest
            if not params.get('file') and has_folder(folder):
                try:
                    stat_info = os.stat(folder)
                    time_struct = time.localtime(stat_info.st_mtime)
                    snap['INSTALLDATE'] = time.strftime("%d/%m/%Y", time_struct)
                except (OSError, ValueError):
                    pass
            
            packages.append(snap)
        
        return packages
    
    @staticmethod
    def _get_packages_info(**params) -> None:
        """Get detailed package info."""
        snap = params.get('snap')
        if not snap:
            return
        
        Snap._parse_snap_yaml(
            logger=params.get('logger'),
            snap=snap,
            file=params.get('file')
        )
        
        if params.get('command'):
            # snap info command may wrongly output some long infos
            old_columns = os.environ.get('COLUMNS')
            os.environ['COLUMNS'] = '100'
            
            Snap._parse_snap_yaml(
                logger=params.get('logger'),
                snap=snap,
                command=params['command']
            )
            
            # Restore environment
            if old_columns:
                os.environ['COLUMNS'] = old_columns
            elif 'COLUMNS' in os.environ:
                del os.environ['COLUMNS']
        
        if not snap or not snap.get('NAME'):
            return
        
        # Cleanup publisher from 'starred' if verified
        if snap.get('PUBLISHER'):
            snap['PUBLISHER'] = re.sub(r'[*]$', '', snap['PUBLISHER'])
            if re.match(r'^[-]+$', snap['PUBLISHER']):
                del snap['PUBLISHER']
    
    @staticmethod
    def _parse_snap_yaml(**params) -> None:
        """Parse snap YAML output."""
        snap = params.get('snap')
        if not snap:
            return
        
        arch = False
        mapping_keys = '|'.join(sorted(Snap.MAPPING.keys()))
        mapping_pattern = rf'({mapping_keys}):\s+(.+)$'
        
        for line in get_all_lines(**params):
            if arch:
                match = re.match(r'^\s*-\s(.*)$', line)
                if match:
                    snap['ARCH'] = match.group(1)
                arch = False
            elif line.startswith('architectures:'):
                arch = True
            elif re.match(r'^[\s-]', line):
                continue
            elif re.match(r'^installed:\s+.*\(.*\)\s+(\d+\S+)', line):
                match = re.match(r'^installed:\s+.*\(.*\)\s+(\d+\S+)', line)
                if match:
                    size = get_canonical_size(match.group(1), 1024)
                    if size:
                        snap['FILESIZE'] = int(size * 1048576)
            else:
                match = re.match(mapping_pattern, line)
                if match:
                    key, value = match.groups()
                    snap[Snap.MAPPING[key]] = value
