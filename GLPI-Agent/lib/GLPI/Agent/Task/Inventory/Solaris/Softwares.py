#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Solaris Softwares - Python Implementation
"""

import re
from typing import Any, Optional, List, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines, get_canonical_size, month


class Softwares(InventoryModule):
    """Solaris software packages detection module."""
    
    category = "software"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('pkg') or can_run('pkginfo')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        pkgs = Softwares._parse_pkgs(logger=logger)
        if not pkgs:
            return
        
        for pkg in pkgs:
            if inventory:
                inventory.add_entry(
                    section='SOFTWARES',
                    entry=pkg
                )
    
    @staticmethod
    def _parse_pkgs(**params) -> Optional[List[Dict[str, Any]]]:
        """Parse package information."""
        if 'command' not in params:
            if can_run('pkg'):
                params['command'] = 'pkg info'
            else:
                params['command'] = 'pkginfo -l'
        
        lines = get_all_lines(**params)
        if not lines:
            return None
        
        softwares = []
        software = {}
        use_pkg_info = 'pkg info' in params['command']
        
        if use_pkg_info:
            for line in lines:
                if re.match(r'^\s*$', line):
                    if software:
                        softwares.append(software)
                        software = {}
                elif line.startswith('Name:'):
                    match = re.match(r'Name:\s+(.+)', line)
                    if match:
                        software['NAME'] = match.group(1)
                elif line.startswith('Version:'):
                    match = re.match(r'Version:\s+(.+)', line)
                    if match:
                        software['VERSION'] = match.group(1)
                elif 'FMRI:' in line and not software.get('VERSION'):
                    match = re.search(r'FMRI:\s+.+\@(.+)', line)
                    if match:
                        software['VERSION'] = match.group(1)
                elif line.startswith('Publisher:'):
                    match = re.match(r'Publisher:\s+(.+)', line)
                    if match:
                        software['PUBLISHER'] = match.group(1)
                elif line.startswith('Summary:'):
                    match = re.match(r'Summary:\s+(.+)', line)
                    if match:
                        software['COMMENTS'] = match.group(1)
                elif 'Last Install Time:' in line:
                    match = re.match(r'Last Install Time:\s+\S+\s+(\S+)\s+(\d+)\s+\S+\s+(\d+)$', line)
                    if match:
                        try:
                            from datetime import datetime
                            dt = datetime(
                                month=month(match.group(1)),
                                day=int(match.group(2)),
                                year=int(match.group(3))
                            )
                            software['INSTALLDATE'] = dt.strftime('%d/%m/%Y')
                        except Exception:
                            pass
                elif line.startswith('Size:'):
                    match = re.match(r'Size:\s+(.+)$', line)
                    if match:
                        size = get_canonical_size(match.group(1), 1024)
                        if size is not None:
                            software['FILESIZE'] = int(size)
        else:
            # pkginfo -l format
            for line in lines:
                if re.match(r'^\s*$', line):
                    if software:
                        softwares.append(software)
                        software = {}
                elif line.startswith('PKGINST:'):
                    match = re.match(r'PKGINST:\s+(.+)', line)
                    if match:
                        software['NAME'] = match.group(1)
                elif line.startswith('VERSION:'):
                    match = re.match(r'VERSION:\s+(.+)', line)
                    if match:
                        software['VERSION'] = match.group(1)
                elif line.startswith('VENDOR:'):
                    match = re.match(r'VENDOR:\s+(.+)', line)
                    if match:
                        software['PUBLISHER'] = match.group(1)
                elif line.startswith('DESC:'):
                    match = re.match(r'DESC:\s+(.+)', line)
                    if match:
                        software['COMMENTS'] = match.group(1)
                elif line.startswith('INSTDATE:'):
                    match = re.match(r'INSTDATE:\s+(\S+)\s+(\d+)\s+(\d+)', line)
                    if match:
                        try:
                            from datetime import datetime
                            dt = datetime(
                                month=month(match.group(1)),
                                day=int(match.group(2)),
                                year=int(match.group(3))
                            )
                            software['INSTALLDATE'] = dt.strftime('%d/%m/%Y')
                        except Exception:
                            pass
        
        if software:
            softwares.append(software)
        
        return softwares
