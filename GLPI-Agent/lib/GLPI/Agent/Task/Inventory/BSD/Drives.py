#!/usr/bin/env python3
"""
GLPI Agent Task Inventory BSD Drives - Python Implementation
"""

import re
from typing import Any, List, Dict, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines
from GLPI.Agent.Tools.Unix import (
    get_filesystems_types_from_mount,
    get_filesystems_from_df
)


# Module-level cache for zpool status
_zpool_status_cache: Dict[str, Dict] = {}


class Drives(InventoryModule):
    """BSD Drives inventory module."""
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "drive"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('df')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        zpool = can_run('zpool')
        
        # Check we can run geli command to lookup encrypted fs
        geli = None
        if can_run('geom'):
            geli = Drives._get_geli_list(logger=logger)
        
        # get filesystem types
        types = get_filesystems_types_from_mount(logger=logger)
        # Filter out virtual filesystems
        types = [t for t in types if t not in [
            'fdesc', 'devfs', 'procfs', 'linprocfs', 'linsysfs',
            'tmpfs', 'fdescfs'
        ]]
        
        # get filesystem for each type
        filesystems = []
        for fs_type in types:
            found_fs = get_filesystems_from_df(
                logger=logger,
                command=f"df -P -k -t {fs_type}",
                type=fs_type
            )
            
            # Check for geli encryption
            if geli and found_fs:
                for fs in found_fs:
                    encrypted = None
                    volumn = fs.get('VOLUMN')
                    
                    if fs_type == 'zfs' and zpool and volumn:
                        status = Drives._get_zpool_status(volumn=volumn, logger=logger)
                        if status and status.get('config'):
                            # Find .eli volumes in config
                            encrypted_vols = [k for k in status['config'].keys() if k.endswith('.eli')]
                            if encrypted_vols:
                                encrypted = encrypted_vols[0]
                    else:
                        if volumn:
                            match = re.search(r'/([^/]+\.eli)$', volumn)
                            if match:
                                encrypted = match.group(1)
                    
                    if encrypted and encrypted in geli:
                        fs['ENCRYPT_NAME'] = 'geli'
                        geli_state = geli[encrypted].get('state', '')
                        fs['ENCRYPT_STATUS'] = 'Yes' if re.match(r'^ACTIVE$', geli_state, re.IGNORECASE) else 'No'
                        fs['ENCRYPT_ALGO'] = geli[encrypted].get('algo')
                        fs['ENCRYPT_TYPE'] = geli[encrypted].get('type')
            
            if found_fs:
                filesystems.extend(found_fs)
        
        # add filesystems to the inventory
        for filesystem in filesystems:
            if inventory:
                inventory.add_entry(
                    section='DRIVES',
                    entry=filesystem
                )
    
    @staticmethod
    def _get_zpool_status(**params) -> Optional[Dict]:
        """Get zpool status with caching."""
        global _zpool_status_cache
        
        volumn = params.get('volumn')
        if not volumn:
            return None
        
        # Extract pool name from volume
        match = re.match(r'^([^/]+)', volumn)
        if not match:
            return None
        
        pool = match.group(1)
        
        # Return cached status if available
        if pool in _zpool_status_cache:
            return _zpool_status_cache[pool]
        
        logger = params.get('logger')
        lines = get_all_lines(command=f"zpool status {pool}", logger=logger)
        if not lines:
            return None
        
        status = {}
        for line in lines:
            if not line.strip():
                continue
            
            # Key-value pairs
            match = re.match(r'^\s*(\w+)\s*:\s*(\w.*)$', line)
            if match:
                status[match.group(1)] = match.group(2)
                continue
            
            # Config section start
            if re.match(r'^\s*config\s*:', line):
                status['config'] = {}
                continue
            
            # Config entries
            if 'config' in status:
                match = re.match(r'^\s*(\S+)\s+(\w+)\s+\w+\s+\w+\s+\w+', line)
                if match:
                    name, state = match.groups()
                    if name != 'NAME':  # Skip header
                        status['config'][name] = state
        
        # Cache the status
        _zpool_status_cache[pool] = status
        
        return status
    
    @staticmethod
    def _get_geli_list(**params) -> Optional[Dict[str, Dict[str, str]]]:
        """Get list of geli encrypted volumes."""
        geli = {}
        
        # Get list of geli volumes
        status_lines = get_all_lines(command="geom eli status -s", **params)
        if not status_lines:
            return None
        
        for status_line in status_lines:
            match = re.match(r'^(\S+)\s', status_line)
            if not match:
                continue
            
            volumn = match.group(1)
            
            # Get details for this volume
            detail_lines = get_all_lines(command=f"geom eli list {volumn}", **params)
            if not detail_lines:
                continue
            
            geli[volumn] = {}
            
            for line in detail_lines:
                if not line.strip():
                    continue
                
                # Parse State
                match = re.match(r'^State:\s*(\S+)$', line)
                if match:
                    geli[volumn]['state'] = match.group(1)
                
                # Parse EncryptionAlgorithm
                match = re.match(r'^EncryptionAlgorithm:\s*(\S+)$', line)
                if match:
                    geli[volumn]['algo'] = match.group(1)
                
                # Parse KeyLength
                match = re.match(r'^KeyLength:\s*(\S+)$', line)
                if match:
                    geli[volumn]['keysize'] = match.group(1)
                
                # Parse Crypto
                match = re.match(r'^Crypto:\s*(\S+)$', line)
                if match:
                    geli[volumn]['type'] = match.group(1)
            
            # Fix algo with keysize
            if 'algo' in geli[volumn] and 'keysize' in geli[volumn]:
                geli[volumn]['algo'] = f"{geli[volumn]['algo']}-{geli[volumn]['keysize']}"
                del geli[volumn]['keysize']
        
        return geli if geli else None
