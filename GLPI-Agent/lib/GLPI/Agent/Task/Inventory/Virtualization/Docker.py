#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Virtualization Docker - Python Implementation
"""

import json
from typing import Any, List, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines
from GLPI.Agent.Tools.Virtualization import STATUS_RUNNING, STATUS_OFF


class Docker(InventoryModule):
    """Docker containers detection module."""
    
    # wanted info fields for each container
    WANTED_INFOS = ['ID', 'Image', 'Ports', 'Names']
    
    # formatting separator
    SEPARATOR = '#=#=#'
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('docker')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        # formatting with a Go template (required by docker ps command)
        wanted = ['{{.' + field + '}}' for field in Docker.WANTED_INFOS]
        template = Docker.SEPARATOR.join(wanted)
        
        for container in Docker._get_containers(
            logger=logger,
            command=f'docker ps -a --format "{template}"'
        ):
            if inventory:
                inventory.add_entry(
                    section='VIRTUALMACHINES',
                    entry=container
                )
    
    @staticmethod
    def _get_containers(**params) -> List[Dict[str, Any]]:
        """Get Docker containers."""
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        containers = []
        for line in lines:
            info = line.split(Docker.SEPARATOR)
            if len(info) != len(Docker.WANTED_INFOS):
                continue
            
            status = ''
            if params.get('command'):
                status = Docker._get_status(
                    command=f'docker inspect {info[0]}'
                )
            
            container = {
                'VMTYPE': 'docker',
                'UUID': info[0],
                'IMAGE': info[1],
                'NAME': info[3],
                'STATUS': status
            }
            
            containers.append(container)
        
        return containers
    
    @staticmethod
    def _get_status(**params) -> str:
        """Get container status."""
        lines = get_all_lines(**params)
        status = ''
        
        try:
            container_data = json.loads('\n'.join(lines))
            
            running = False
            if isinstance(container_data, list):
                running = container_data[0].get('State', {}).get('Running', False) if container_data else False
            elif isinstance(container_data, dict):
                running = container_data.get('State', {}).get('Running', False)
            
            status = STATUS_RUNNING if running else STATUS_OFF
        except (json.JSONDecodeError, IndexError, KeyError, TypeError):
            pass
        
        return status
