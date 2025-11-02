#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Virtualization HyperV - Python Implementation
"""

import sys
from typing import Any, List, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools.Virtualization import (STATUS_RUNNING, STATUS_OFF, STATUS_PAUSED,
                                             STATUS_BLOCKED, STATUS_SHUTDOWN)


class HyperV(InventoryModule):
    """Microsoft Hyper-V virtual machines detection module."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return sys.platform == 'win32'
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        
        for machine in HyperV._get_virtual_machines():
            if inventory:
                inventory.add_entry(
                    section='VIRTUALMACHINES',
                    entry=machine
                )
    
    @staticmethod
    def _get_virtual_machines() -> List[Dict[str, Any]]:
        """Get Hyper-V virtual machines via WMI."""
        try:
            from GLPI.Agent.Tools.Win32 import get_wmi_objects
        except ImportError:
            return []
        
        machines = []
        
        # index memory, cpu and BIOS UUID information
        memory = {}
        for obj in get_wmi_objects(
            moniker='winmgmts://./root/virtualization/v2',
            altmoniker='winmgmts://./root/virtualization',
            class_name='MSVM_MemorySettingData',
            properties=['InstanceID', 'VirtualQuantity']
        ):
            instance_id = obj.get('InstanceID', '')
            if instance_id.startswith('Microsoft:'):
                vm_id = instance_id.split('Microsoft:')[1].split('\\')[0]
                memory[vm_id] = obj.get('VirtualQuantity')
        
        vcpu = {}
        for obj in get_wmi_objects(
            moniker='winmgmts://./root/virtualization/v2',
            altmoniker='winmgmts://./root/virtualization',
            class_name='MSVM_ProcessorSettingData',
            properties=['InstanceID', 'VirtualQuantity']
        ):
            instance_id = obj.get('InstanceID', '')
            if instance_id.startswith('Microsoft:'):
                vm_id = instance_id.split('Microsoft:')[1].split('\\')[0]
                vcpu[vm_id] = obj.get('VirtualQuantity')
        
        biosguid = {}
        for obj in get_wmi_objects(
            moniker='winmgmts://./root/virtualization/v2',
            altmoniker='winmgmts://./root/virtualization',
            class_name='MSVM_VirtualSystemSettingData',
            properties=['InstanceID', 'BIOSGUID']
        ):
            instance_id = obj.get('InstanceID', '')
            bios_guid = obj.get('BIOSGUID')
            if bios_guid and instance_id.startswith('Microsoft:'):
                vm_id = instance_id.split('Microsoft:')[1].split('\\')[0]
                biosguid[vm_id] = bios_guid.replace('{', '').replace('}', '')
        
        for obj in get_wmi_objects(
            moniker='winmgmts://./root/virtualization/v2',
            altmoniker='winmgmts://./root/virtualization',
            class_name='MSVM_ComputerSystem',
            properties=['ElementName', 'EnabledState', 'Name', 'InstallDate']
        ):
            # skip host as it has no InstallDate
            if not obj.get('InstallDate'):
                continue
            
            enabled_state = obj.get('EnabledState', 0)
            status = (
                STATUS_RUNNING if enabled_state == 2 else
                STATUS_OFF if enabled_state == 3 else
                STATUS_PAUSED if enabled_state == 32768 else
                STATUS_OFF if enabled_state == 32769 else
                STATUS_BLOCKED if enabled_state in [32770, 32771, 32773, 32776, 32777] else
                STATUS_SHUTDOWN if enabled_state == 32774 else
                STATUS_OFF
            )
            
            name = obj.get('Name', '')
            machine = {
                'SUBSYSTEM': 'MS HyperV',
                'VMTYPE': 'HyperV',
                'STATUS': status,
                'NAME': obj.get('ElementName'),
                'UUID': biosguid.get(name),
                'MEMORY': memory.get(name),
                'VCPU': vcpu.get(name)
            }
            
            machines.append(machine)
        
        return machines
