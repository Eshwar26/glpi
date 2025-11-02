#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux OS - Python Implementation
"""

from typing import Any, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, Uname, get_first_line, get_first_match, has_file, get_formated_local_time
from GLPI.Agent.Tools.Unix import get_root_fs_birth


class OS(InventoryModule):
    """Linux OS information detection module."""
    
    category = "os"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return True
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        kernel_release = Uname('-r')
        
        hostid = get_first_line(
            logger=logger,
            command='hostid'
        )
        
        os = {
            'HOSTID': hostid,
            'KERNEL_VERSION': kernel_release,
        }
        
        installdate = OS._get_operating_system_install_date(logger=logger)
        if installdate:
            os['INSTALL_DATE'] = installdate
        
        if inventory:
            inventory.set_operating_system(os)
    
    @staticmethod
    def _get_operating_system_install_date(**params) -> Optional[str]:
        """Get operating system installation date."""
        # Check for basesystem package installation date on rpm base systems
        if can_run('rpm'):
            time = OS._rpm_basesystem_install_date(**params)
            if time:
                return time
        
        # Check for dpkg based systems (debian, ubuntu)
        if has_file('/var/lib/dpkg/info/base-files.list'):
            return OS._debian_install_date()
        
        # Otherwise read birth date of root file system
        return get_root_fs_birth(**params)
    
    @staticmethod
    def _rpm_basesystem_install_date(**params) -> Optional[str]:
        """Get basesystem package install date from RPM."""
        if 'command' not in params:
            params['command'] = "rpm -q --queryformat '%{INSTALLTIME}\\n' basesystem"
        
        date_str = get_first_line(**params)
        if not date_str:
            return None
        
        try:
            # Try to use DateTime if available
            import datetime
            dt = datetime.datetime.fromtimestamp(int(date_str))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            # Fall back to getFormatedLocalTime
            try:
                return get_formated_local_time(int(date_str))
            except Exception:
                return None
    
    @staticmethod
    def _debian_install_date(**params) -> Optional[str]:
        """Get install date from Debian base-files."""
        if 'command' not in params:
            params['command'] = 'stat -c %w /var/lib/dpkg/info/base-files.list'
        
        return get_first_match(
            pattern=r'^(\d+-\d+-\d+\s\d+:\d+:\d+)',
            **params
        )
