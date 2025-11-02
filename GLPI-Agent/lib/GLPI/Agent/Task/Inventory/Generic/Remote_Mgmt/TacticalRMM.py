#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Remote_Mgmt TacticalRMM - Python Implementation
"""

import json
import platform
import re
from typing import Any, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, has_file, get_all_lines, get_first_line, get_sanitized_string


class TacticalRMM(InventoryModule):
    """TacticalRMM remote management inventory module."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        osname = platform.system()
        logger = params.get('logger')
        
        if osname == 'Windows':
            from GLPI.Agent.Tools.Win32 import get_registry_key
            
            key = get_registry_key(
                path='HKEY_LOCAL_MACHINE/SOFTWARE/TacticalRMM/',
                required=['AgentId'],
                maxdepth=1,
                logger=logger
            )
            
            return bool(key and len(key) > 0)
        
        elif osname == 'Linux':
            return has_file('/etc/tacticalagent')
        
        elif osname == 'Darwin':
            return has_file('/private/etc/tacticalagent')
        
        return False
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        version = TacticalRMM._get_version(logger=logger)
        agent_id = TacticalRMM._get_agent_id(logger=logger)
        if not agent_id:
            return
        
        mgmt = {
            'ID': agent_id,
            'TYPE': 'tacticalrmm',
        }
        if version:
            mgmt['VERSION'] = version
        
        if inventory:
            inventory.add_entry(
                section='REMOTE_MGMT',
                entry=mgmt
            )
    
    @staticmethod
    def _get_agent_id(**params) -> Optional[str]:
        """Get TacticalRMM Agent ID."""
        osname = platform.system()
        
        if osname == 'Windows':
            return TacticalRMM._win_based(**params)
        elif osname == 'Linux':
            return TacticalRMM._linux_based(**params)
        elif osname == 'Darwin':
            return TacticalRMM._macos_based(**params)
        
        return None
    
    @staticmethod
    def _macos_based(**params) -> Optional[str]:
        """Get Agent ID from macOS."""
        config = get_all_lines(
            file='/private/etc/tacticalagent',
            **params
        )
        
        if not config:
            return None
        
        try:
            config_str = '\n'.join(config) if isinstance(config, list) else config
            data = json.loads(config_str)
            return data.get('agentid')
        except (json.JSONDecodeError, TypeError):
            return None
    
    @staticmethod
    def _linux_based(**params) -> Optional[str]:
        """Get Agent ID from Linux."""
        config = get_all_lines(
            file='/etc/tacticalagent',
            **params
        )
        
        if not config:
            return None
        
        try:
            config_str = '\n'.join(config) if isinstance(config, list) else config
            data = json.loads(config_str)
            return data.get('agentid')
        except (json.JSONDecodeError, TypeError):
            return None
    
    @staticmethod
    def _win_based(**params) -> Optional[str]:
        """Get Agent ID from Windows registry."""
        from GLPI.Agent.Tools.Win32 import get_registry_value
        
        return get_registry_value(
            path='HKEY_LOCAL_MACHINE/SOFTWARE/TacticalRMM/AgentId',
            logger=params.get('logger')
        )
    
    @staticmethod
    def _get_version(**params) -> Optional[str]:
        """Get TacticalRMM agent version."""
        osname = platform.system()
        
        if osname == 'Windows':
            command = r'"C:\Program Files\TacticalAgent\tacticalrmm.exe" --version'
        elif can_run('rmmagent'):
            command = 'rmmagent --version'
        elif can_run('tacticalagent'):
            command = 'tacticalagent --version'
        elif osname == 'Darwin':
            command = '/opt/tacticalagent/tacticalagent --version'
        else:
            command = '/usr/local/bin/rmmagent --version'
        
        # On windows, the command seems to output a BOM on the first line
        line = get_sanitized_string(get_first_line(
            command=command,
            **params
        ))
        
        if not line:
            return None
        
        match = re.search(r'Tactical RMM Agent:\s+([0-9.]+)', line, re.IGNORECASE)
        return match.group(1) if match else None
