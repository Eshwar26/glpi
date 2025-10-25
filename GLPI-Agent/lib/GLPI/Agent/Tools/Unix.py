#!/usr/bin/env python3
"""
GLPI Agent Tools Unix - Python Implementation

Unix-specific generic functions for system information gathering.
"""

import os
import re
import time
import glob as glob_module
from pathlib import Path
from typing import Dict, List, Optional, Any, Pattern
from datetime import datetime

# Import the main Tools module functions
try:
    from GLPI.Agent.Tools import (get_all_lines, get_first_line, get_first_match,
                                   has_folder, glob_files, file_stat, has_link,
                                   read_link, has_file, get_os_name, can_run)
    from GLPI.Agent.Tools.Network import ip_address_pattern, network_pattern, mac_address_pattern
except ImportError:
    import sys
    sys.path.insert(0, '../../')
    from Tools import (get_all_lines, get_first_line, get_first_match,
                       has_folder, glob_files, file_stat, has_link,
                       read_link, has_file, get_os_name, can_run)
    # Mock network patterns for standalone usage
    ip_address_pattern = r'\d{1,3}(?:\.\d{1,3}){3}'
    network_pattern = r'\d{1,3}(?:\.\d{1,3}){3}/\d{1,2}'
    mac_address_pattern = r'(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}'


__all__ = [
    'get_device_capacity',
    'get_ip_dhcp',
    'get_filesystems_from_df',
    'get_filesystems_types_from_mount',
    'get_processes',
    'get_routing_table',
    'get_root_fs_birth',
    'get_xauthority_file'
]


def get_device_capacity(**params) -> Optional[int]:
    """
    Returns storage capacity of given device, using fdisk.
    
    Args:
        **params: Parameters including:
            - device: The device to query
            - logger: Logger object
            - root: Root directory for testing
            - dump: Dictionary to store command outputs
            
    Returns:
        Device capacity in MB or None
    """
    device = params.get('device')
    if not device:
        return None
    
    logger = params.pop('logger', None)
    root = params.get('root', '')
    dump = params.get('dump')
    
    # Get device name
    from os.path import basename
    name = basename(device)
    
    # Check fdisk version
    params['command'] = "/sbin/fdisk -v"
    if dump:
        dump['fdisk-v'] = get_all_lines(**params)
    
    if root:
        params['file'] = f"{root}/fdisk-v"
    
    first_line = get_first_line(**params)
    
    # GNU version requires -p flag
    if first_line and first_line.startswith('GNU'):
        params['command'] = f"/sbin/fdisk -p -s {device}"
    else:
        params['command'] = f"/sbin/fdisk -s {device}"
    
    # Always override with a file if testing under $root
    if root:
        params['file'] = f"{root}/fdisk-{name}"
    
    if dump:
        dump[f'fdisk-{name}'] = get_all_lines(logger=logger, **params)
    
    capacity_str = get_first_line(logger=logger, **params)
    
    if capacity_str:
        try:
            capacity = int(capacity_str) // 1000
            return capacity
        except ValueError:
            return None
    
    return None


def get_ip_dhcp(logger, interface: str) -> Optional[str]:
    """
    Returns DHCP server IP for an interface.
    
    Args:
        logger: Logger object
        interface: Network interface name
        
    Returns:
        DHCP server IP address or None
    """
    dhcp_lease_file = _find_dhcp_lease_file(interface)
    
    if not dhcp_lease_file:
        return None
    
    return _parse_dhcp_lease_file(logger, interface, dhcp_lease_file)


def _find_dhcp_lease_file(interface: str) -> Optional[str]:
    """
    Find DHCP lease file for an interface.
    
    Args:
        interface: Network interface name
        
    Returns:
        Path to lease file or None
    """
    directories = [
        '/var/db',
        '/var/lib/dhcp3',
        '/var/lib/dhcp',
        '/var/lib/dhclient'
    ]
    
    patterns = [f"*{interface}*.lease", "*.lease", f"dhclient.leases.{interface}"]
    files = []
    
    for directory in directories:
        if not has_folder(directory):
            continue
        
        for pattern in patterns:
            full_pattern = os.path.join(directory, pattern)
            files.extend(glob_module.glob(full_pattern))
    
    if not files:
        return None
    
    # Sort by creation time and take the last one
    files_with_stat = []
    for f in files:
        try:
            stat_info = os.stat(f)
            files_with_stat.append((f, stat_info.st_ctime))
        except OSError:
            continue
    
    if not files_with_stat:
        return None
    
    files_with_stat.sort(key=lambda x: x[1])
    return files_with_stat[-1][0]


def _parse_dhcp_lease_file(logger, interface: str, lease_file: str) -> Optional[str]:
    """
    Parse DHCP lease file to extract server IP.
    
    Args:
        logger: Logger object
        interface: Network interface name
        lease_file: Path to lease file
        
    Returns:
        DHCP server IP or None
    """
    lines = get_all_lines(file=lease_file, logger=logger)
    if not lines:
        return None
    
    lease = False
    dhcp = False
    server_ip = None
    expiration_time = None
    
    for line in lines:
        if re.match(r'^lease', line, re.I):
            lease = True
            continue
        
        if line.startswith('}'):
            lease = False
            continue
        
        if not lease:
            continue
        
        # Inside a lease section
        match = re.search(r'interface\s+"([^"]+)"', line)
        if match:
            dhcp = (match.group(1) == interface)
            continue
        
        if not dhcp:
            continue
        
        # Server IP
        match = re.search(r'option\s+dhcp-server-identifier\s+(\d{1,3}(?:\.\d{1,3}){3})', line, re.X)
        if match:
            server_ip = match.group(1)
        
        # Expiration time
        match = re.search(
            r'expire\s+\d\s+(\d+)/(\d+)/(\d+)\s+(\d+):(\d+):(\d+)',
            line, re.X
        )
        if match:
            year, mon, day, hour, min_val, sec = map(int, match.groups())
            # Warning: month expected range is 0-11, not 1-12
            mon -= 1
            try:
                dt = datetime(year, mon + 1, day, hour, min_val, sec)
                expiration_time = int(dt.timestamp())
            except ValueError:
                pass
    
    if not expiration_time:
        return None
    
    current_time = int(time.time())
    
    return server_ip if current_time <= expiration_time else None


def get_filesystems_from_df(**params) -> List[Dict[str, Any]]:
    """
    Returns a list of filesystems by parsing df command output.
    
    Args:
        **params: Parameters including:
            - command: Command to run
            - file: File to read
            - type: Filesystem type if not in df output
            - logger: Logger object
            
    Returns:
        List of filesystem dictionaries
    """
    lines = get_all_lines(**params)
    if not lines:
        return []
    
    filesystems = []
    
    # Get headers line first
    header = lines.pop(0) if lines else None
    if not header:
        return []
    
    headers = header.split()
    
    for line in lines:
        infos = line.split()
        if len(infos) < 4:
            continue
        
        # Depending on the df implementation, filesystem type may appear as second column
        if len(headers) > 1 and headers[1] == 'Type':
            if len(infos) < 7:
                continue
            filesystem = infos[1]
            total = infos[2]
            used = infos[3]
            free = infos[4]
            volumn = infos[0]
            type_val = infos[6] if len(infos) > 6 else ''
        else:
            filesystem = params.get('type', '')
            total = infos[1]
            used = infos[2]
            free = infos[3]
            volumn = infos[0]
            type_val = infos[5] if len(infos) > 5 else ''
        
        # Fix total for zfs under Solaris
        try:
            total_int = int(total)
            used_int = int(used)
            free_int = int(free)
        except ValueError:
            continue
        
        if not total_int and (used_int or free_int):
            total_int = used_int + free_int
        
        # Skip some virtual filesystems
        if total_int == 0 or free_int == 0:
            continue
        
        filesystems.append({
            'VOLUMN': volumn,
            'FILESYSTEM': filesystem,
            'TOTAL': total_int // 1024,
            'FREE': free_int // 1024,
            'TYPE': type_val
        })
    
    return filesystems


def get_filesystems_types_from_mount(**params) -> List[str]:
    """
    Returns a list of used filesystem types by parsing mount command output.
    
    Args:
        **params: Parameters including:
            - command: Command to run (default: mount)
            - file: File to read
            - logger: Logger object
            
    Returns:
        List of unique filesystem types
    """
    if 'command' not in params:
        params['command'] = 'mount'
    
    lines = get_all_lines(**params)
    if not lines:
        return []
    
    types = []
    for line in lines:
        # BSD-style: /dev/mirror/gm0s1d on / (ufs, local, soft-updates)
        match = re.match(r'^\S+ on \S+ \((\w+)', line)
        if match:
            types.append(match.group(1))
            continue
        
        # Linux style: /dev/sda2 on / type ext4 (rw,noatime,errors=remount-ro)
        match = re.match(r'^\S+ on \S+ type (\w+)', line)
        if match:
            types.append(match.group(1))
            continue
    
    # Return unique types
    return list(set(types))


def get_processes(**params) -> List[Dict[str, Any]]:
    """
    Returns a list of processes by parsing ps command output.
    
    Args:
        **params: Parameters including:
            - command: Command to run
            - logger: Logger object
            - namespace: Filter by namespace ('same' for current namespace)
            - filter: Regex pattern to filter commands
            
    Returns:
        List of process dictionaries
    """
    # Check if ps is busybox
    ps_path = None
    if can_run('ps'):
        ps_path = get_first_line(command="which ps")
    
    if ps_path and has_link(ps_path) and read_link(ps_path) == 'busybox':
        return _get_processes_busybox(**params)
    else:
        return _get_processes_other(**params)


def _get_processes_busybox(**params) -> List[Dict[str, Any]]:
    """
    Get processes from busybox ps command.
    
    Args:
        **params: Parameters
        
    Returns:
        List of process dictionaries
    """
    if 'command' not in params:
        params['command'] = 'ps'
    
    lines = get_all_lines(**params)
    if not lines:
        return []
    
    # Skip headers
    if lines:
        lines.pop(0)
    
    processes = []
    
    for line in lines:
        match = re.match(r'^\s*(\S+)\s+(\S+)\s+(\S+)\s+...\s+(\S.+)', line, re.X)
        if not match:
            continue
        
        pid = match.group(1)
        user = match.group(2)
        vsz = match.group(3)
        cmd = match.group(4)
        
        processes.append({
            'USER': user,
            'PID': pid,
            'VIRTUALMEMORY': vsz,
            'CMD': cmd
        })
    
    return processes


def _get_processes_other(**params) -> List[Dict[str, Any]]:
    """
    Get processes from standard ps command.
    
    Args:
        **params: Parameters
        
    Returns:
        List of process dictionaries
    """
    os_name = get_os_name()
    
    if 'command' not in params:
        comm_field = 'comm' if os_name == 'solaris' else 'command'
        params['command'] = f'ps -A -o user,pid,pcpu,pmem,vsz,tty,etime,{comm_field}'
    
    # Support a parameter to only keep processes from the same namespace
    same_namespace = params.pop('namespace', '')
    namespace_value = 0
    with_namespace = False
    
    if os_name != 'solaris' and same_namespace == 'same':
        # Extract namespace number from the system first process
        ns_line = get_first_line(
            command="ps --no-headers -o cgroupns 1",
            logger=params.get('logger')
        )
        if ns_line and ns_line.strip().isdigit():
            namespace_value = int(ns_line.strip())
            comm_field = 'comm' if os_name == 'solaris' else 'command'
            params['command'] = f'ps -A -o user,pid,pcpu,pmem,vsz,tty,etime,cgroupns,{comm_field}'
            with_namespace = True
    
    filter_pattern = params.pop('filter', None)
    if filter_pattern and not isinstance(filter_pattern, Pattern):
        filter_pattern = None
    
    lines = get_all_lines(**params)
    if not lines:
        return []
    
    # Skip headers
    if lines:
        lines.pop(0)
    
    # Get the current timestamp
    localtime = int(time.time())
    
    processes = []
    
    for line in lines:
        if with_namespace:
            match = re.match(
                r'^\s*(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S.*\S)',
                line, re.X
            )
            if not match:
                continue
            
            user, pid, cpu, mem, vsz, tty, etime, ns, cmd = match.groups()
            
            # Filter by namespace
            if namespace_value and ns.isdigit() and int(ns) != namespace_value:
                continue
        else:
            match = re.match(
                r'^\s*(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S.*\S)',
                line, re.X
            )
            if not match:
                continue
            
            user, pid, cpu, mem, vsz, tty, etime, cmd = match.groups()
        
        # Filter by command pattern
        if filter_pattern and not filter_pattern.search(cmd):
            continue
        
        processes.append({
            'USER': user,
            'PID': pid,
            'CPUUSAGE': cpu,
            'MEM': mem,
            'VIRTUALMEMORY': vsz,
            'TTY': tty,
            'STARTED': _get_process_start_time(localtime, etime),
            'CMD': cmd
        })
    
    return processes


def _get_process_start_time(localtime: int, elapsedtime_string: str) -> Optional[str]:
    """
    Computes a consistent process starting time from the process etime value.
    
    Args:
        localtime: Current timestamp
        elapsedtime_string: Elapsed time string from ps
        
    Returns:
        Formatted start time string or None
    """
    # POSIX specifies that ps etime entry looks like [[dd-]hh:]mm:ss
    parts = re.split(r'\D', elapsedtime_string)
    parts.reverse()
    
    psec = int(parts[0]) if len(parts) > 0 else None
    pmin = int(parts[1]) if len(parts) > 1 else None
    phour = int(parts[2]) if len(parts) > 2 else 0
    pday = int(parts[3]) if len(parts) > 3 else 0
    
    if psec is None or pmin is None:
        return None
    
    # Compute a timestamp from the process etime value
    elapsedtime = psec + pmin * 60 + phour * 60 * 60 + pday * 24 * 60 * 60
    
    # Subtract this timestamp from the current time
    start_time = localtime - elapsedtime
    dt = datetime.fromtimestamp(start_time)
    
    # Output the final date
    return dt.strftime("%Y-%m-%d %H:%M")


def get_routing_table(**params) -> Dict[str, str]:
    """
    Returns the routing table as a dictionary by parsing netstat command output.
    
    Args:
        **params: Parameters including:
            - command: Command to run (default: netstat -nr -f inet)
            - file: File to read
            - logger: Logger object
            
    Returns:
        Dictionary mapping destinations to gateways
    """
    if 'command' not in params:
        params['command'] = 'netstat -nr -f inet'
    
    lines = get_all_lines(**params)
    if not lines:
        return {}
    
    routes = {}
    
    # First, skip all header lines
    while lines:
        line = lines.pop(0)
        if re.match(r'^Destination', line):
            break
    
    # Second, collect routes
    pattern = re.compile(
        rf'^({ip_address_pattern}|{network_pattern}|default)\s+'
        rf'({ip_address_pattern}|{mac_address_pattern}|link\#\d+)',
        re.X
    )
    
    for line in lines:
        match = pattern.match(line)
        if not match:
            continue
        
        dest = match.group(1)
        gateway = match.group(2)
        
        # Don't override a route as the first one is the more specific
        if dest not in routes:
            routes[dest] = gateway
    
    return routes


def get_root_fs_birth(**params) -> Optional[str]:
    """
    Returns the root filesystem birth date by parsing stat / command output.
    
    Args:
        **params: Parameters including:
            - command: Command to run (default: stat /)
            - logger: Logger object
            
    Returns:
        Birth date string or None
    """
    if 'command' not in params:
        params['command'] = 'stat /'
    
    if 'pattern' not in params:
        params['pattern'] = re.compile(r'^\s*Birth:\s+(\d+-\d+-\d+\s\d+:\d+:\d+)')
    
    return get_first_match(**params)


def get_xauthority_file(**params) -> Optional[str]:
    """
    Returns the first found XAuthority file of any current X server user.
    
    Args:
        **params: Parameters including:
            - logger: Logger object
            
    Returns:
        Path to .Xauthority file or None
    """
    # First identify users using X
    users = {}
    x11_sockets = glob_module.glob("/tmp/.X11-unix/*")
    
    for unix_socket in x11_sockets:
        try:
            stat_info = os.stat(unix_socket)
            users[stat_info.st_uid] = True
        except OSError:
            continue
    
    if not users:
        return None
    
    # Then find first user's process using XAUTHORITY environment
    proc_dirs = glob_module.glob("/proc/*/environ")
    pids = []
    for proc_dir in proc_dirs:
        match = re.match(r'/proc/(\d+)/environ', proc_dir)
        if match:
            pids.append(int(match.group(1)))
    
    pids.sort()
    
    stats_cache = {}
    for uid in users:
        for pid in pids:
            file_path = f"/proc/{pid}/environ"
            
            # Cache file stat
            if file_path not in stats_cache:
                try:
                    stats_cache[file_path] = os.stat(file_path)
                except OSError:
                    stats_cache[file_path] = None
            
            stat_info = stats_cache[file_path]
            if not stat_info or stat_info.st_uid != uid:
                continue
            
            lines = get_all_lines(file=file_path, no_error_log=True, **params)
            if not lines:
                continue
            
            content = ''.join(lines)
            env_vars = content.split('\0')
            
            for env_var in env_vars:
                if env_var.startswith('XAUTHORITY='):
                    xauthority = env_var.split('=', 1)[1]
                    if xauthority and has_file(xauthority):
                        return xauthority
    
    return None


if __name__ == '__main__':
    print("GLPI Agent Tools Unix Module")
    print("Unix-specific generic functions")
