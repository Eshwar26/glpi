#!/usr/bin/env python3
"""
GLPI Agent Tools Solaris - Python Implementation

Solaris generic functions for system information gathering.
"""

import re
from typing import Dict, List, Optional, Any, Callable

# Import the main Tools module functions
try:
    from GLPI.Agent.Tools import (get_all_lines, get_first_line, can_run, 
                                   get_canonical_size, trim_whitespace)
except ImportError:
    import sys
    sys.path.insert(0, '../../')
    from Tools import (get_all_lines, get_first_line, can_run,
                       get_canonical_size, trim_whitespace)


__all__ = [
    'get_zone',
    'get_prtconf_infos',
    'get_prtdiag_infos',
    'get_release_info',
    'get_smbios'
]


def get_zone() -> str:
    """
    Returns current zone name, or 'global' if there is no defined zone.
    
    Returns:
        Zone name or 'global'
    """
    if can_run('zonename'):
        zone = get_first_line(command='zonename')
        return zone if zone else 'global'
    return 'global'


def get_prtconf_infos(**params) -> Optional[Dict[str, Any]]:
    """
    Returns a structured view of prtconf output.
    Each information block is turned into a dict, hierarchically organised.
    
    Args:
        **params: Parameters including:
            - command: Command to run (default: /usr/sbin/prtconf -vp)
            - file: File to read instead of running command
            - logger: Logger object
            
    Returns:
        Dictionary containing parsed prtconf data
    """
    if 'command' not in params:
        params['command'] = '/usr/sbin/prtconf -vp'
    
    lines = get_all_lines(**params)
    if not lines:
        return None
    
    info = {}
    
    # A stack of nodes, as a list of tuples [node, level]
    parents = [
        [info, -1]
    ]
    
    for line in lines:
        # New node
        match = re.match(r'^(\s*)Node \s 0x[a-f\d]+', line, re.X)
        if match:
            level = len(match.group(1)) if match.group(1) else 0
            parent_level = parents[-1][1]
            
            # Compare level with parent
            if level > parent_level:
                # Down the tree: no change
                pass
            elif level < parent_level:
                # Up the tree: unstack nodes until a suitable parent is found
                while level <= parents[-1][1]:
                    parents.pop()
            else:
                # Same level: unstack last node
                parents.pop()
            
            # Push a new node on the stack
            parents.append([{}, level])
            continue
        
        # Node name
        match = re.match(r"^\s*name:\s+'(\S.*)'$", line)
        if match:
            node = parents[-1][0]
            parent = parents[-2][0]
            parent[match.group(1)] = node
            continue
        
        # Value
        match = re.match(r'^\s*(\S[^:]+):\s+(\S.*)$', line)
        if match:
            key = match.group(1)
            raw_value = match.group(2)
            node = parents[-1][0]
            
            # List of string values
            if re.match(r"^'[^']+'(?: \+ '[^']+')+$", raw_value):
                node[key] = [
                    re.match(r"^'([^']+)'$", v).group(1)
                    for v in re.split(r' \+ ', raw_value)
                ]
            # Single string value
            elif re.match(r"^'([^']+)'$", raw_value):
                match_val = re.match(r"^'([^']+)'$", raw_value)
                node[key] = match_val.group(1)
            # Other kind of value
            else:
                node[key] = raw_value
            continue
    
    return info


def get_prtdiag_infos(**params) -> Optional[Dict[str, Any]]:
    """
    Returns a structured view of prtdiag output.
    
    Args:
        **params: Parameters including:
            - command: Command to run (default: prtdiag)
            - file: File to read instead of running command
            - logger: Logger object
            
    Returns:
        Dictionary containing parsed prtdiag data
    """
    if 'command' not in params:
        params['command'] = 'prtdiag'
    
    lines = get_all_lines(**params)
    if not lines:
        return None
    
    info = {}
    
    while lines:
        line = lines.pop(0)
        
        match = re.match(r'^=+\s([\w\s]+)\s=+$', line, re.X)
        if not match:
            continue
        
        section = match.group(1)
        
        if 'Memory' in section:
            info['memories'] = _parse_memory_section(section, lines)
        
        if re.search(r'(IO|Slots)', section):
            info['slots'] = _parse_slots_section(section, lines)
    
    return info


def _parse_memory_section(section: str, lines: List[str]) -> Optional[List[Dict[str, Any]]]:
    """
    Parse memory section from prtdiag output.
    
    Args:
        section: Section name
        lines: Remaining lines to parse
        
    Returns:
        List of memory information dictionaries
    """
    offset = 0
    callback = None
    
    if section == 'Physical Memory Configuration':
        i = [0]  # Use list to allow modification in nested function
        offset = 5
        
        def callback_fn(line):
            match = re.search(r'(\d+\s[MG]B)\s+\S+$', line, re.X)
            if not match:
                return []
            result = {
                'TYPE': 'DIMM',
                'NUMSLOTS': i[0],
                'CAPACITY': get_canonical_size(match.group(1), 1024)
            }
            i[0] += 1
            return [result]
        
        callback = callback_fn
    
    elif section == 'Memory Configuration':
        # Use next line to determine actual format
        if not lines:
            return None
        
        next_line = lines.pop(0)
        
        # Skip next line if empty
        if next_line and re.match(r'^\s*$', next_line):
            if lines:
                next_line = lines.pop(0)
            else:
                return None
        
        if not next_line:
            return None
        
        if re.match(r'^Segment Table', next_line):
            # Multi-table format: reach bank table
            while lines:
                next_line = lines.pop(0)
                if re.match(r'^Bank Table', next_line):
                    break
            
            i = [0]
            offset = 4
            
            def callback_fn(line):
                match = re.search(r'\d+\s+\S+\s+\S+\s+(\d+[MG]B)', line, re.X)
                if not match:
                    return []
                result = {
                    'TYPE': 'DIMM',
                    'NUMSLOTS': i[0],
                    'CAPACITY': get_canonical_size(match.group(1), 1024)
                }
                i[0] += 1
                return [result]
            
            callback = callback_fn
        
        elif re.search(r'Memory\s+Available\s+Memory\s+DIMM\s+#\sof', next_line):
            i = [0]
            offset = 2
            
            def callback_fn(line):
                match = re.search(r'\d+[MG]B\s+\S+\s+(\d+[MG]B)\s+(\d+)\s+', line, re.X)
                if not match:
                    return []
                results = []
                count = int(match.group(2))
                for _ in range(count):
                    results.append({
                        'TYPE': 'DIMM',
                        'NUMSLOTS': i[0],
                        'CAPACITY': get_canonical_size(match.group(1), 1024)
                    })
                    i[0] += 1
                return results
            
            callback = callback_fn
        
        else:
            i = [0]
            offset = 3
            
            def callback_fn(line):
                match = re.search(r'(\d+[MG]B)\s+\S+\s+(\d+[MG]B)\s+\S+\s+', line, re.X)
                if not match:
                    return []
                dimmsize = get_canonical_size(match.group(2), 1024)
                logicalsize = get_canonical_size(match.group(1), 1024)
                # Compute DIMM count from "Logical Bank Size" and "DIMM Size"
                dimmcount = 1
                if dimmsize and dimmsize != logicalsize:
                    dimmcount = int(logicalsize / dimmsize)
                
                results = []
                for _ in range(dimmcount):
                    results.append({
                        'TYPE': 'DIMM',
                        'NUMSLOTS': i[0],
                        'CAPACITY': dimmsize
                    })
                    i[0] += 1
                return results
            
            callback = callback_fn
    
    elif section == 'Memory Device Sockets':
        i = [0]
        offset = 3
        
        def callback_fn(line):
            match = re.match(
                r'^(\w+)\s+in\suse\s+\d\s+([A-Za-z]+)\d*(?:\s\w+)*',
                line, re.X
            )
            if not match:
                return []
            result = {
                'DESCRIPTION': match.group(2),
                'NUMSLOTS': i[0],
                'TYPE': match.group(1)
            }
            i[0] += 1
            return [result]
        
        callback = callback_fn
    
    else:
        return None
    
    return _parse_any_section(lines, offset, callback)


def _parse_slots_section(section: str, lines: List[str]) -> Optional[List[Dict[str, Any]]]:
    """
    Parse slots section from prtdiag output.
    
    Args:
        section: Section name
        lines: Remaining lines to parse
        
    Returns:
        List of slot information dictionaries
    """
    offset = 0
    callback = None
    
    if section == 'IO Devices':
        offset = 3
        
        def callback_fn(line):
            match = re.match(r'^(\S+)\s+([A-Z]+)\s+(\S+)', line, re.X)
            if not match:
                return []
            return [{
                'NAME': match.group(1),
                'DESCRIPTION': match.group(2),
                'DESIGNATION': match.group(3)
            }]
        
        callback = callback_fn
    
    elif section == 'IO Cards':
        offset = 7
        
        def callback_fn(line):
            match = re.match(
                r'^\S+\s+([A-Z]+)\s+\S+\s+\S+\s+(\d)\s+\S+\s+\S+\s+\S+\s+\S+\s+(\S+)',
                line, re.X
            )
            if not match:
                return []
            return [{
                'NAME': match.group(2),
                'DESCRIPTION': match.group(1),
                'DESIGNATION': match.group(3)
            }]
        
        callback = callback_fn
    
    elif section == 'Upgradeable Slots':
        offset = 3
        
        def callback_fn(line):
            # Use column-based strategy
            if len(line) < 31:
                return []
            
            name = line[0:1]
            status = line[4:13].rstrip()
            description = line[14:30].rstrip()
            designation = line[31:59].rstrip() if len(line) > 31 else ""
            
            status_map = {
                'in use': 'used',
                'available': 'free'
            }
            status = status_map.get(status)
            
            return [{
                'NAME': name,
                'STATUS': status,
                'DESCRIPTION': description,
                'DESIGNATION': designation
            }]
        
        callback = callback_fn
    
    else:
        return None
    
    return _parse_any_section(lines, offset, callback)


def _parse_any_section(lines: List[str], offset: int, 
                       callback: Optional[Callable]) -> Optional[List[Dict[str, Any]]]:
    """
    Generic section parser.
    
    Args:
        lines: Lines to parse
        offset: Number of header lines to skip
        callback: Function to parse each line
        
    Returns:
        List of parsed items
    """
    if not callback:
        return None
    
    # Skip headers
    for _ in range(offset):
        if lines:
            lines.pop(0)
    
    # Parse content
    items = []
    while lines:
        line = lines.pop(0)
        if not line or re.match(r'^$', line):
            break
        
        item_list = callback(line)
        if item_list:
            items.extend(item_list)
    
    return items if items else None


def get_release_info(**params) -> Optional[Dict[str, Any]]:
    """
    Get Solaris release information from /etc/release.
    
    Args:
        **params: Parameters including:
            - file: File to read (default: /etc/release)
            - logger: Logger object
            
    Returns:
        Dictionary containing release information
    """
    if 'file' not in params:
        params['file'] = '/etc/release'
    
    first_line = get_first_line(**params)
    if not first_line:
        return None
    
    match = re.match(r'^\s+(.+)', first_line)
    if not match:
        return None
    
    fullname = match.group(1)
    version = None
    date = None
    id_val = None
    subversion = None
    
    if 'Solaris' in fullname:
        match = re.search(r'Solaris\s([\d.]+)\s(?:(\d+/\d+)\s)?(\S+)', fullname, re.X)
        if match:
            version = match.group(1)
            date = match.group(2)
            id_val = match.group(3)
            
            if id_val:
                sub_match = re.search(r'_(u\d+)', id_val)
                if sub_match:
                    subversion = sub_match.group(1)
    
    elif 'OpenIndiana' in fullname:
        match = re.search(r'([\d.]+)', fullname)
        if match:
            version = match.group(1)
    
    elif re.search(r'^OmniOS v(\d+) r(\d+)', fullname):
        match = re.match(r'^OmniOS v(\d+) r(\d+)', fullname)
        if match:
            version = match.group(1)
            subversion = match.group(2)
    
    return {
        'fullname': fullname,
        'version': version,
        'subversion': subversion,
        'date': date,
        'id': id_val
    }


def get_smbios(**params) -> Optional[Dict[str, Any]]:
    """
    Parse smbios command output.
    
    Args:
        **params: Parameters including:
            - command: Command to run (default: /usr/sbin/smbios)
            - file: File to read instead of running command
            - logger: Logger object
            
    Returns:
        Dictionary containing parsed smbios data
    """
    if 'command' not in params:
        params['command'] = '/usr/sbin/smbios'
    
    lines = get_all_lines(**params)
    if not lines:
        return None
    
    # Force to register last parsed element
    lines.append("ID    SIZE TYPE")
    
    infos = {}
    current = None
    key = None
    section = None
    
    while lines:
        line = lines.pop(0)
        
        if re.match(r'^ID\s+SIZE\s+TYPE', line, re.X):
            if section:
                if section in infos:
                    existing = infos[section]
                    if isinstance(existing, list):
                        existing.append(current)
                    elif isinstance(existing, dict):
                        infos[section] = [existing, current]
                    else:
                        infos[section] = [existing, current]
                else:
                    infos[section] = current
            
            current = {}
            section = None
            key = None
        
        elif re.match(r'^(\t|\s{4})\S', line):
            # Skip flags details
            continue
        
        elif re.match(r'^\d+\s+\d+\s+(\S+)', line, re.X):
            match = re.match(r'^\d+\s+\d+\s+(\S+)', line, re.X)
            section = match.group(1)
        
        elif re.match(r'^\s+(?:offset:)?\s+0 1 2 3  4 5 6 7  8 9 a b  c d e f\s+0123456789abcdef$', line):
            while lines and re.match(r'^\s+\d+:\s+([0-9a-f ]+)\s\|?\s', lines[0]):
                hexdump_line = lines.pop(0)
                match = re.match(r'^\s+\d+:\s+([0-9a-f ]+)\s\|?\s', hexdump_line)
                hexdump = match.group(1).replace(' ', '')
                
                if key:
                    if isinstance(current, dict) and key in current:
                        if isinstance(current[key], str):
                            current[key] += hexdump
                    else:
                        if isinstance(current, dict):
                            current[key] = "0x" + hexdump
                else:
                    if isinstance(current, str):
                        current += hexdump
                    elif isinstance(current, dict):
                        current = "0x" + hexdump if not current else current
        
        else:
            match = re.match(r'^\s*([^:]+)(?:\s\([^:]+\))?:\s*(.+)?$', line, re.X)
            if match:
                key = match.group(1)
                value = trim_whitespace(match.group(2)) if match.group(2) else None
                if isinstance(current, dict):
                    current[key] = value
            else:
                match = re.match(r'^  (.+)$', line)
                if match:
                    value = trim_whitespace(match.group(1))
                    if key:
                        if isinstance(current, dict):
                            if key in current:
                                existing_val = current[key]
                                if isinstance(existing_val, list):
                                    existing_val.append(value)
                                elif existing_val is not None:
                                    current[key] = [existing_val, value]
                                else:
                                    current[key] = value
                            else:
                                current[key] = value
    
    return infos


if __name__ == '__main__':
    print("GLPI Agent Tools Solaris Module")
    print("Solaris generic functions")
