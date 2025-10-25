"""
GLPI Agent Task Inventory Vmsystem Module

Detects virtual machine system type.
"""

import re
from typing import List, Optional, Dict


# Virtualization detection patterns
VMWARE_PATTERNS = [
    'Hypervisor detected: VMware',
    'VMware vmxnet3? virtual NIC driver',
    'Vendor: VMware\s+Model: Virtual disk',
    'Vendor: VMware,\s+Model: VMware Virtual ',
    ': VMware Virtual IDE CDROM Drive'
]

QEMU_PATTERNS = [
    ' QEMUAPIC ',
    'QEMU Virtual CPU',
    ': QEMU HARDDISK,',
    ': QEMU CD-ROM,',
    ': QEMU Standard PC',
    'Hypervisor detected: KVM',
    'Booting paravirtualized kernel on KVM'
]

VIRTUAL_MACHINE_PATTERNS = [
    ': Virtual HD,',
    ': Virtual CD,'
]

VIRTUALBOX_PATTERNS = [
    ' VBOXBIOS ',
    ': VBOX HARDDISK,',
    ': VBOX CD-ROM,',
]

XEN_PATTERNS = [
    'Hypervisor signature: xen',
    'Xen virtual console successfully installed',
    'Xen reported:',
    'Xen: \d+ - \d+',
    'xen-vbd: registered block device',
    'ACPI: [A-Z]{4} \(v\d+\s+Xen ',
]

# Module patterns for kernel module detection
MODULE_PATTERNS = {
    'VMware': re.compile(r'^vmxnet\s'),
    'Xen': re.compile(r'^xen_\w+front\s'),
}


class Vmsystem:
    """Virtual machine system detection module"""
    
    # Run after modules that can set BIOS or HARDWARE (only setting UUID)
    run_after_if_enabled = [
        'GLPI.Agent.Task.Inventory.AIX.Bios',
        'GLPI.Agent.Task.Inventory.BSD.Alpha',
        'GLPI.Agent.Task.Inventory.BSD.i386',
        'GLPI.Agent.Task.Inventory.BSD.MIPS',
        'GLPI.Agent.Task.Inventory.BSD.SPARC',
        'GLPI.Agent.Task.Inventory.Generic.Dmidecode.Bios',
        'GLPI.Agent.Task.Inventory.Generic.Dmidecode.Hardware',
        'GLPI.Agent.Task.Inventory.HPUX.Bios',
        'GLPI.Agent.Task.Inventory.HPUX.Hardware',
        'GLPI.Agent.Task.Inventory.Linux.Bios',
        'GLPI.Agent.Task.Inventory.Linux.PowerPC.Bios',
        'GLPI.Agent.Task.Inventory.Linux.Hardware',
        'GLPI.Agent.Task.Inventory.Linux.ARM.Board',
        'GLPI.Agent.Task.Inventory.MacOS.Bios',
        'GLPI.Agent.Task.Inventory.MacOS.Hardware',
        'GLPI.Agent.Task.Inventory.Solaris.Bios',
        'GLPI.Agent.Task.Inventory.Solaris.Hardware',
        'GLPI.Agent.Task.Inventory.Win32.Bios',
        'GLPI.Agent.Task.Inventory.Win32.Hardware',
    ]
    
    @staticmethod
    def is_enabled() -> bool:
        """Check if module is enabled (always enabled)"""
        return True
    
    @staticmethod
    def _assemble_patterns(patterns: List[str]) -> re.Pattern:
        """Assemble patterns into a single compiled regex"""
        combined = '|'.join(f'(?:{p})' for p in patterns)
        return re.compile(combined, re.IGNORECASE)
    
    @classmethod
    def _get_type(cls, inventory=None, logger=None) -> Optional[str]:
        """
        Determine the virtual machine type.
        
        Args:
            inventory: Inventory instance
            logger: Logger instance
        
        Returns:
            VM type string or None
        """
        # Placeholder - would check various sources:
        # 1. DMI/SMBIOS manufacturer
        # 2. systemd-detect-virt
        # 3. dmesg output
        # 4. /proc files
        # 5. kernel modules
        # 6. hypervisor detection
        
        # For now, return None (not detected)
        return None
    
    @classmethod
    def do_inventory(cls, inventory=None, logger=None, **params) -> None:
        """
        Execute the inventory.
        
        Args:
            inventory: Inventory instance
            logger: Logger instance
            **params: Additional parameters
        """
        if not inventory:
            return
        
        vm_type = cls._get_type(inventory, logger)
        
        if not vm_type:
            return
        
        # Handle Xen special case
        if vm_type == 'Xen':
            manufacturer = inventory.get_bios('SMANUFACTURER') if hasattr(inventory, 'get_bios') else None
            if not manufacturer:
                inventory.set_bios({
                    'SMANUFACTURER': 'Xen',
                    'SMODEL': 'PVM domU'
                })
        
        # Handle Virtuozzo special case
        if vm_type == 'Virtuozzo':
            # Compute compound identifier for Virtuozzo
            host_id = inventory.get_hardware('UUID') if hasattr(inventory, 'get_hardware') else ''
            
            # Try to get envID from /proc/self/status
            guest_id = ''
            try:
                with open('/proc/self/status', 'r') as f:
                    for line in f:
                        match = re.match(r'^envID:\s*(\d+)', line)
                        if match:
                            guest_id = match.group(1)
                            break
            except (IOError, OSError):
                pass
            
            if host_id and guest_id:
                inventory.set_hardware({'UUID': f'{host_id}-{guest_id}'})
        
        # Handle Docker special case
        if vm_type == 'Docker':
            # Get container ID
            container_id = None
            try:
                with open('/proc/self/cgroup', 'r') as f:
                    for line in f:
                        match = re.search(r'docker[/-]([0-9a-f]{64})', line)
                        if match:
                            container_id = match.group(1)
                            break
            except (IOError, OSError):
                pass
            
            if container_id:
                # Use first 12 chars as short ID
                inventory.set_hardware({'UUID': container_id[:12]})
        
        # Set the VM system type
        if logger:
            logger.debug(f"Virtual machine type: {vm_type}")
        
        # Would call inventory.setVmsystem or similar
        # inventory.set_vmsystem(vm_type)
