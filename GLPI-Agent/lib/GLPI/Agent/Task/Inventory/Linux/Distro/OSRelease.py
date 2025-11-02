#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux Distro OSRelease - Python Implementation
"""

import re
from typing import Any, Optional, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_read, get_all_lines, get_first_line, get_first_match, trim_whitespace


class OSRelease(InventoryModule):
    """Linux distribution detection via /etc/os-release."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_read('/etc/os-release')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        
        os = OSRelease._get_os_release(file='/etc/os-release')
        
        # Handle Debian case where version is not complete like in Ubuntu
        # by checking /etc/debian_version
        if can_read('/etc/debian_version'):
            OSRelease._fix_debian_os(file='/etc/debian_version', os=os)
        
        # Handle Astra Linux information
        if can_read('/etc/astra/build_version'):
            OSRelease._fix_astra_os(os=os)
        
        # Handle CentOS case as version is not well-defined on this distro
        # See https://bugs.centos.org/view.php?id=8359
        if can_read('/etc/centos-release'):
            if not os.get('VERSION') or re.match(r'^\d+ ', os['VERSION']):
                OSRelease._fix_centos(file='/etc/centos-release', os=os)
        
        if inventory:
            inventory.set_operating_system(os)
    
    @staticmethod
    def _get_os_release(**params) -> Dict[str, Any]:
        """Parse /etc/os-release file."""
        lines = get_all_lines(**params)
        if not lines:
            return {}
        
        os = {}
        for line in lines:
            name_match = re.match(r'^NAME="?([^"]+)"?', line)
            if name_match:
                os['NAME'] = name_match.group(1)
            
            version_match = re.match(r'^VERSION="?([^"]+)"?', line)
            if version_match:
                os['VERSION'] = version_match.group(1)
            
            full_name_match = re.match(r'^PRETTY_NAME="?([^"]+)"?', line)
            if full_name_match:
                os['FULL_NAME'] = full_name_match.group(1)
        
        return os
    
    @staticmethod
    def _fix_debian_os(**params) -> None:
        """Fix Debian OS version information."""
        os = params.get('os', {})
        
        debian_version = get_first_line(**params)
        if debian_version and re.match(r'^\d', debian_version):
            os['VERSION'] = debian_version
    
    @staticmethod
    def _fix_astra_os(**params) -> None:
        """Fix Astra Linux OS information."""
        os = params.get('os')
        if not os:
            os = {}
            params['os'] = os
        
        # Support unittest via build in params
        build_file = params.get('build', '/etc/astra/build_version')
        version = get_first_line(file=build_file)
        if version and re.match(r'^\d', version):
            os['VERSION'] = version
        
        # Support unittest via license in params
        license_file = params.get('license', '/etc/astra_license')
        if not can_read(license_file):
            return
        
        edition = get_first_match(
            pattern=r'^DESCRIPTION="?(.*?)"?$',
            file=license_file
        )
        
        if edition:
            # Extract security level
            if re.match(r'^([^\s()]+)\s*\(', edition):
                match = re.match(r'^([^\s()]+)\s*\(', edition)
                security_level = match.group(1)
            elif re.search(r'\(([^\s()]+)\)', edition):
                match = re.search(r'\(([^\s()]+)\)', edition)
                security_level = match.group(1)
            elif re.search(r'\(([^)]+)\)', edition):
                match = re.search(r'\(([^)]+)\)', edition)
                parts = match.group(1).split()
                security_level = parts[0] if parts else 'unknown'
            else:
                security_level = 'unknown'
            
            security_level = trim_whitespace(security_level) if security_level else 'unknown'
            
            if os.get('FULL_NAME'):
                os['FULL_NAME'] = re.sub(r'\(.*?\)', '', os['FULL_NAME'])
                os['FULL_NAME'] = f"{trim_whitespace(os['FULL_NAME'])} (Security level: {security_level})"
    
    @staticmethod
    def _fix_centos(**params) -> None:
        """Fix CentOS version information."""
        os = params.get('os', {})
        
        centos_release = get_first_line(**params)
        if not centos_release:
            return
        
        match = re.match(r'^CentOS .* ([0-9.]+.*)$', centos_release)
        if match:
            os['VERSION'] = match.group(1)
