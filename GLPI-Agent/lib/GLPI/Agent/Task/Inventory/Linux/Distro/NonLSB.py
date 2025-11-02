#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux Distro NonLSB - Python Implementation
"""

import os
import re
from typing import Any, List, Optional, Dict, Tuple

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import first, has_file, get_first_line, get_first_match


class NonLSB(InventoryModule):
    """Linux distribution detection for non-LSB systems."""
    
    # This array contains four items for each distribution:
    # - release file
    # - distribution name
    # - regex to get the version
    # - template to get the full name
    DISTRIBUTIONS = [
        # vmware-release contains something like "VMware ESX Server 3" or "VMware ESX 4.0 (Kandinsky)"
        ['/etc/vmware-release', 'VMWare', r'([\d.]+)', '%s'],
        
        ['/etc/arch-release', 'ArchLinux', r'(.*)', 'ArchLinux'],
        
        ['/etc/debian_version', 'Debian', r'(.*)', 'Debian GNU/Linux %s'],
        
        # fedora-release contains something like "Fedora release 9 (Sulphur)"
        ['/etc/fedora-release', 'Fedora', r'release ([\d.]+)', '%s'],
        
        ['/etc/gentoo-release', 'Gentoo', r'(.*)', 'Gentoo Linux %s'],
        
        # knoppix_version contains something like "3.2 2003-04-15".
        # Note: several 3.2 releases can be made, with different dates, so we need to keep the date suffix
        ['/etc/knoppix_version', 'Knoppix', r'(.*)', 'Knoppix GNU/Linux %s'],
        
        # mandriva-release contains something like "Mandriva Linux release 2010.1 (Official) for x86_64"
        ['/etc/mandriva-release', 'Mandriva', r'release ([\d.]+)', '%s'],
        
        # mandrake-release contains something like "Mandrakelinux release 10.1 (Community) for i586"
        ['/etc/mandrake-release', 'Mandrake', r'release ([\d.]+)', '%s'],
        
        # oracle-release contains something like "Oracle Linux Server release 6.3"
        ['/etc/oracle-release', 'Oracle Linux Server', r'release ([\d.]+)', '%s'],
        
        # centos-release contains something like "CentOS Linux release 6.0 (Final)"
        ['/etc/centos-release', 'CentOS', r'release ([\d.]+)', '%s'],
        
        # redhat-release contains something like "Red Hat Enterprise Linux Server release 5 (Tikanga)"
        ['/etc/redhat-release', 'RedHat', r'release ([\d.]+)', '%s'],
        
        ['/etc/slackware-version', 'Slackware', r'Slackware (.*)', '%s'],
        
        # SuSE-release contains something like "SUSE Linux Enterprise Server 11 (x86_64)"
        # Note: it may contain several extra lines
        ['/etc/SuSE-release', 'SuSE', r'([\d.]+)', '%s'],
        
        # trustix-release contains something like "Trustix Secure Linux release 2.0 (Cloud)"
        ['/etc/trustix-release', 'Trustix', r'release ([\d.]+)', '%s'],
        
        # Fallback
        ['/etc/issue', 'Unknown Linux distribution', r'([\d.]+)', '%s'],
        
        # Note: Ubuntu is not listed here as it does not have a
        # ubuntu-{release,version} file, but it should always have the lsb_release
        # command so it will be handled by the Linux::Distro::LSB module
    ]
    
    runMeIfTheseChecksFailed = [
        "GLPI::Agent::Task::Inventory::Linux::Distro::OSRelease"
    ]
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        # Run only if os-release is not available
        from GLPI.Agent.Tools import can_read
        return not can_read('/etc/os-release')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        
        distribution = first(
            lambda d: has_file(d[0]),
            NonLSB.DISTRIBUTIONS
        )
        if not distribution:
            return
        
        data = NonLSB._get_distro_data(distribution)
        
        if inventory:
            inventory.set_operating_system(data)
    
    @staticmethod
    def _get_distro_data(distribution: List) -> Dict[str, Any]:
        """Extract distribution data from release file."""
        name = distribution[1]
        regexp = distribution[2]
        template = distribution[3]
        
        line = get_first_line(file=distribution[0])
        
        # Arch Linux has an empty release file
        release = None
        version = None
        
        if line:
            release = template % line
            match = re.search(regexp, line)
            if match:
                version = match.group(1)
        else:
            release = template
        
        # If the detected OS is RedHat, but the release contains Scientific, then it is Scientific
        if 'RedHat' in name:
            if release and 'Scientific' in release:
                # this is really a scientific linux, we have to change the name
                name = 'Scientific'
        
        data = {
            'NAME': name,
            'VERSION': version,
            'FULL_NAME': release
        }
        
        if name == 'SuSE':
            # SLES15 doesn't have /etc/SuSE-release
            if os.path.exists('/etc/SuSE-release'):
                data['SERVICE_PACK'] = get_first_match(
                    file='/etc/SuSE-release',
                    pattern=r'^PATCHLEVEL = ([0-9]+)'
                )
            else:
                # fall back by checking if there's a -SP in the current version
                # if so, split by -SP
                if version and re.search(r'\-SP.+', version):
                    match = re.match(r'(.*)-SP(.*)', version)
                    if match:
                        data['VERSION'], data['SERVICE_PACK'] = match.groups()
        
        return data
