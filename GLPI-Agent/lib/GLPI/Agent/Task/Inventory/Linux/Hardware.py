#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux Hardware - Python Implementation
"""

from typing import Any, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import has_folder, has_file, get_first_line, get_all_lines


class Hardware(InventoryModule):
    """Linux hardware detection module."""
    
    category = "hardware"
    
    runAfterIfEnabled = ["GLPI::Agent::Task::Inventory::Generic::Dmidecode::Hardware"]
    
    # Follow dmidecode dmi_chassis_type() API
    # See https://github.com/mirror/dmidecode/blob/master/dmidecode.c#L593
    CHASSIS_TYPES = [
        "",
        "Other",
        "Unknown",
        "Desktop",
        "Low Profile Desktop",
        "Pizza Box",
        "Mini Tower",
        "Tower",
        "Portable",
        "Laptop",
        "Notebook",
        "Hand Held",
        "Docking Station",
        "All in One",
        "Sub Notebook",
        "Space-Saving",
        "Lunch Box",
        "Main Server Chassis",
        "Expansion Chassis",
        "Sub Chassis",
        "Bus Expansion Chassis",
        "Peripheral Chassis",
        "RAID Chassis",
        "Rack Mount Chassis",
        "Sealed-case PC",
        "Multi-system",
        "CompactPCI",
        "AdvancedTCA",
        "Blade",
        "Blade Enclosing",
        "Tablet",
        "Convertible",
        "Detachable",
        "IoT Gateway",
        "Embedded PC",
        "Mini PC",
        "Stick PC",
    ]
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return True
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        
        hardware = {}
        
        system_id = Hardware._get_rhn_system_id('/etc/sysconfig/rhn/systemid')
        if system_id:
            hardware['WINPRODID'] = system_id
        
        uuid = Hardware._dmi_info('product_uuid')
        if uuid:
            hardware['UUID'] = uuid
        
        chassis_type_str = Hardware._dmi_info('chassis_type')
        if chassis_type_str:
            try:
                chassis_type = int(chassis_type_str)
                if 0 <= chassis_type < len(Hardware.CHASSIS_TYPES):
                    hardware['CHASSIS_TYPE'] = Hardware.CHASSIS_TYPES[chassis_type]
            except (ValueError, IndexError):
                pass
        
        if hardware and inventory:
            inventory.set_hardware(hardware)
    
    @staticmethod
    def _get_rhn_system_id(file: str) -> Optional[str]:
        """Get RedHat Network SystemId."""
        if not has_file(file):
            return None
        
        try:
            from GLPI.Agent.XML import XML
            content = get_all_lines(file=file)
            if not content:
                return None
            
            content_str = ''.join(content) if isinstance(content, list) else content
            xml = XML(string=content_str)
            if not xml:
                return None
            
            h = xml.dump_as_hash()
            members = h.get('params', {}).get('param', {}).get('value', {}).get('struct', {}).get('member', [])
            for member in members:
                if member.get('name') == 'system_id':
                    return member.get('value', {}).get('string')
        except Exception:
            pass
        
        return None
    
    @staticmethod
    def _dmi_info(info: str) -> Optional[str]:
        """Read DMI information from sysfs."""
        class_path = f'/sys/class/dmi/id/{info}'
        if has_folder(class_path):
            return None
        if not has_file(class_path):
            return None
        return get_first_line(file=class_path)
