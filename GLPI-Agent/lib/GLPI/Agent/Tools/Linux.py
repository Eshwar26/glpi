#!/usr/bin/env python3
"""
GLPI Agent Tools Linux - Python Implementation

Linux-specific functions for hardware inventory and system information.

NOTE: This module requires Linux-specific system files and commands.
Full functionality requires: /proc, /sys, udev, smartctl, ip, ifconfig, etc.
"""

import re
import glob as glob_module
import os
from typing import List, Dict, Optional, Any
from pathlib import Path

# Import common tools
try:
    from GLPI.Agent.Tools import (get_all_lines, get_first_line, get_first_match,
                                   glob_files, has_file, has_folder, trim_whitespace,
                                   can_run, get_canonical_manufacturer)
    from GLPI.Agent.Tools.Unix import get_device_capacity
    from GLPI.Agent.Tools.Network import ip_address_pattern, alt2canonical
except ImportError:
    # Stub implementations for testing
    def get_all_lines(**params):
        return []
    def get_first_line(**params):
        return None
    def get_first_match(**params):
        return None
    def glob_files(pattern):
        return []
    def has_file(path):
        return os.path.isfile(path)
    def has_folder(path):
        return os.path.isdir(path)
    def trim_whitespace(s):
        return s.strip() if s else s
    def can_run(cmd):
        return False
    def get_canonical_manufacturer(s):
        return s
    def get_device_capacity(**params):
        return None
    ip_address_pattern = r'\d{1,3}(?:\.\d{1,3}){3}'
    def alt2canonical(addr):
        return addr


__all__ = [
    'get_devices_from_udev',
    'get_devices_from_hal',
    'get_devices_from_proc',
    'get_cpus_from_proc',
    'get_info_from_smartctl',
    'get_interfaces_from_ifconfig',
    'get_interfaces_from_ip',
    'get_interfaces_infos_from_ioctl',
    'get_default_gateway_from_ip'
]


# Linux ioctl constants for ethtool
SIOCETHTOOL = 0x8946
ETHTOOL_GSET = 0x00000001
SPEED_UNKNOWN = 65535


def get_devices_from_udev(**params) -> List[Dict]:
    """
    Get storage devices from udev database.
    
    Args:
        **params: Parameters including logger, root, dump
        
    Returns:
        List of device dictionaries
    """
    devices = []
    root = params.get('root', '')
    dump = params.get('dump')
    
    # Glob udev database files
    pattern = f"{root}/dev/.udev/db/*"
    for file_path in glob_module.glob(pattern):
        if dump and has_file(file_path):
            base = os.path.basename(file_path)
            if 'dev' not in dump:
                dump['dev'] = {}
            if '.udev' not in dump['dev']:
                dump['dev']['.udev'] = {}
            if 'db' not in dump['dev']['.udev']:
                dump['dev']['.udev']['db'] = {}
            dump['dev']['.udev']['db'][base] = get_all_lines(file=file_path)
        
        device_name = get_first_match(
            file=file_path,
            pattern=re.compile(r'^N:(\S+)')
        )
        
        if not device_name:
            continue
        
        # Only process storage devices
        if not re.search(r'([hsv]d[a-z]+|sr\d+)$', device_name):
            continue
        
        parsed = _parse_udev_entry(
            logger=params.get('logger'),
            file=file_path,
            device=device_name
        )
        
        if parsed:
            devices.append(parsed)
    
    # Add disk size for non-CD devices
    for device in devices:
        if device.get('TYPE') == 'cd':
            continue
        
        device['DISKSIZE'] = get_device_capacity(
            device=f"/dev/{device['NAME']}",
            **params
        )
    
    return devices


def _parse_udev_entry(**params) -> Optional[Dict]:
    """Parse a single udev database entry."""
    lines = get_all_lines(**params)
    if not lines:
        return None
    
    result = {}
    serial = None
    
    for line in lines:
        # SCSI information
        match = re.match(r'^S:.*-scsi-(\d+):(\d+):(\d+):(\d+)', line)
        if match:
            result['SCSI_COID'] = match.group(1)
            result['SCSI_CHID'] = match.group(2)
            result['SCSI_UNID'] = match.group(3)
            result['SCSI_LUN'] = match.group(4)
            continue
        
        # Device properties
        if line.startswith('E:ID_VENDOR='):
            result['MANUFACTURER'] = line.split('=', 1)[1]
        elif line.startswith('E:ID_MODEL='):
            result['MODEL'] = line.split('=', 1)[1]
        elif line.startswith('E:ID_REVISION='):
            result['FIRMWARE'] = line.split('=', 1)[1]
        elif line.startswith('E:ID_SERIAL='):
            serial = line.split('=', 1)[1]
        elif line.startswith('E:ID_SERIAL_SHORT='):
            result['SERIALNUMBER'] = line.split('=', 1)[1]
        elif line.startswith('E:ID_TYPE='):
            result['TYPE'] = line.split('=', 1)[1]
        elif line.startswith('E:ID_BUS='):
            result['DESCRIPTION'] = line.split('=', 1)[1]
    
    if not result.get('SERIALNUMBER'):
        result['SERIALNUMBER'] = serial
    
    result['NAME'] = params.get('device')
    
    return result


def get_cpus_from_proc(**params) -> List[Dict]:
    """
    Get CPU information from /proc/cpuinfo.
    
    Args:
        **params: Parameters including file path (default: /proc/cpuinfo)
        
    Returns:
        List of CPU dictionaries
    """
    if 'file' not in params:
        params['file'] = '/proc/cpuinfo'
    
    lines = get_all_lines(**params)
    if not lines:
        return []
    
    cpus = []
    cpu = {}
    
    for line in lines:
        match = re.match(r'^([^:]+\S)\s*:\s(.+)', line)
        if match:
            key = match.group(1).lower().strip()
            value = trim_whitespace(match.group(2))
            cpu[key] = value
        elif not line.strip():
            # Empty line marks end of CPU section
            if cpu and _is_valid_cpu(cpu):
                cpus.append(cpu)
            cpu = {}
    
    # Add last CPU if valid
    if cpu and _is_valid_cpu(cpu):
        cpus.append(cpu)
    
    return cpus


def _is_valid_cpu(cpu: Dict) -> bool:
    """Check if CPU entry is valid."""
    return 'processor' in cpu or 'cpu' in cpu


def get_devices_from_hal(**params) -> List[Dict]:
    """
    Get storage devices from HAL (Hardware Abstraction Layer).
    
    Args:
        **params: Parameters including command, root, dump
        
    Returns:
        List of device dictionaries
    """
    if 'command' not in params:
        params['command'] = '/usr/bin/lshal'
    
    root = params.get('root')
    dump = params.get('dump')
    
    if root:
        params['file'] = f"{root}/lshal"
    elif dump:
        dump['lshal'] = get_all_lines(**params)
    
    lines = get_all_lines(**params)
    if not lines:
        return []
    
    devices = []
    device = None
    
    for line in lines:
        # Start of device entry
        if re.match(r"^udi = '/org/freedesktop/Hal/devices/(storage|legacy_floppy|block)", line):
            device = {}
            continue
        
        if device is None:
            continue
        
        # End of device entry
        if not line.strip():
            devices.append(device)
            device = None
            continue
        
        # Parse device properties
        if 'storage.serial' in line:
            match = re.search(r"storage\.serial\s+=\s+'([^']+)'", line)
            if match:
                device['SERIALNUMBER'] = match.group(1)
        elif 'storage.firmware_version' in line:
            match = re.search(r"storage\.firmware_version\s+=\s+'([^']+)'", line)
            if match:
                device['FIRMWARE'] = match.group(1)
        elif 'block.device' in line:
            match = re.search(r"block\.device\s+=\s+'([^']+)'", line)
            if match:
                dev_match = re.search(r'/dev/(\S+)', match.group(1))
                if dev_match:
                    device['NAME'] = dev_match.group(1)
        elif 'info.vendor' in line:
            match = re.search(r"info\.vendor\s+=\s+'([^']+)'", line)
            if match:
                device['MANUFACTURER'] = match.group(1)
        elif 'storage.model' in line:
            match = re.search(r"storage\.model\s+=\s+'([^']+)'", line)
            if match:
                device['MODEL'] = match.group(1)
        elif 'storage.drive_type' in line:
            match = re.search(r"storage\.drive_type\s+=\s+'([^']+)'", line)
            if match:
                device['TYPE'] = match.group(1)
        elif 'storage.size' in line:
            match = re.search(r'storage\.size\s+=\s+(\S+)', line)
            if match:
                try:
                    size = int(match.group(1))
                    device['DISKSIZE'] = int(size / (1024 * 1024) + 0.5)
                except ValueError:
                    pass
    
    return devices


def get_devices_from_proc(**params) -> List[Dict]:
    """
    Get storage devices from /proc and /sys filesystems.
    
    Args:
        **params: Parameters including logger, root, dump
        
    Returns:
        List of device dictionaries
    """
    # This is a complex function that reads from /sys/block/* and /sys/class/scsi_generic/*
    # For now, provide a stub that maintains the API
    # Full implementation would require extensive /sys filesystem parsing
    
    devices = []
    root = params.get('root', '')
    
    # Simplified implementation - would need full /sys parsing for production
    pattern = f"{root}/sys/block/*"
    for block_path in glob_module.glob(pattern):
        match = re.search(r'([shv]d[a-z]+|fd\d)$', block_path)
        if match:
            name = match.group(1)
            device = {
                'NAME': name,
                'TYPE': 'disk'
            }
            devices.append(device)
    
    return devices


def get_info_from_smartctl(**params) -> Optional[Dict]:
    """
    Get storage device information from smartctl.
    
    Args:
        **params: Parameters including device path
        
    Returns:
        Dictionary with device information or None
    """
    device = params.get('device')
    if not device:
        return None
    
    # Would execute smartctl and parse output
    # Stub for now
    return None


def get_interfaces_from_ifconfig(**params) -> List[Dict]:
    """
    Get network interfaces from ifconfig output.
    
    Args:
        **params: Parameters including command, file, logger
        
    Returns:
        List of interface dictionaries
    """
    if 'command' not in params:
        params['command'] = 'ifconfig -a'
    
    lines = get_all_lines(**params)
    if not lines:
        return []
    
    interfaces = []
    interface = None
    
    for line in lines:
        # New interface starts
        if not line.startswith(' ') and not line.startswith('\t'):
            if interface:
                interfaces.append(interface)
            interface = {}
            
            # Parse interface name
            match = re.match(r'^(\S+)', line)
            if match:
                interface['DESCRIPTION'] = match.group(1)
            
            # Parse MAC address
            match = re.search(rf'({ip_address_pattern}|[0-9a-f:]{{17}})', line, re.I)
            if match:
                addr = match.group(1)
                if ':' in addr:
                    interface['MACADDR'] = addr.lower()
        
        elif interface:
            # Parse IP address
            match = re.search(rf'inet\s+addr:?\s*({ip_address_pattern})', line)
            if match:
                interface['IPADDRESS'] = match.group(1)
            
            # Parse netmask
            match = re.search(rf'mask:?\s*({ip_address_pattern})', line, re.I)
            if match:
                interface['IPMASK'] = match.group(1)
    
    if interface:
        interfaces.append(interface)
    
    return interfaces


def get_interfaces_from_ip(**params) -> List[Dict]:
    """
    Get network interfaces from 'ip' command output.
    
    Args:
        **params: Parameters including command, file, logger
        
    Returns:
        List of interface dictionaries
    """
    if 'command' not in params:
        params['command'] = 'ip -o addr show'
    
    lines = get_all_lines(**params)
    if not lines:
        return []
    
    interfaces = []
    
    for line in lines:
        # Parse ip addr output
        # Format: 1: lo inet 127.0.0.1/8 scope host lo\ ...
        parts = line.split()
        if len(parts) < 4:
            continue
        
        interface = {}
        
        # Interface name (usually second field)
        if len(parts) > 1:
            interface['DESCRIPTION'] = parts[1].rstrip(':')
        
        # IP address with CIDR
        for i, part in enumerate(parts):
            if part in ['inet', 'inet6']:
                if i + 1 < len(parts):
                    addr_cidr = parts[i + 1]
                    if '/' in addr_cidr:
                        addr, prefix = addr_cidr.split('/', 1)
                        if part == 'inet':
                            interface['IPADDRESS'] = addr
                        else:
                            interface['IPADDRESS6'] = addr
        
        if interface:
            interfaces.append(interface)
    
    return interfaces


def get_interfaces_infos_from_ioctl(**params) -> Dict[str, Dict]:
    """
    Get network interface information using ioctl calls.
    
    Args:
        **params: Parameters including logger
        
    Returns:
        Dictionary mapping interface names to information
    """
    # This requires Linux-specific ioctl calls
    # Would need ctypes or fcntl module for proper implementation
    # Stub for now
    return {}


def get_default_gateway_from_ip(**params) -> Optional[str]:
    """
    Get default gateway from 'ip route' command.
    
    Args:
        **params: Parameters including command, file, logger
        
    Returns:
        Default gateway IP address or None
    """
    if 'command' not in params:
        params['command'] = 'ip route show'
    
    lines = get_all_lines(**params)
    if not lines:
        return None
    
    for line in lines:
        if line.startswith('default'):
            match = re.search(rf'via\s+({ip_address_pattern})', line)
            if match:
                return match.group(1)
    
    return None


if __name__ == '__main__':
    print("GLPI Agent Tools Linux Module")
    print("Linux-specific hardware inventory functions")
