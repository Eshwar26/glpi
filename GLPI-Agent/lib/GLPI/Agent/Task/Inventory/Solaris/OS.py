#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Solaris OS - Python Implementation
"""

from datetime import datetime
from typing import Any, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, Uname, get_first_line, get_first_match, empty, month
from GLPI.Agent.Tools.Solaris import get_release_info


class OS(InventoryModule):
    """Solaris OS information detection module."""
    
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
        
        # Operating system information
        info = get_release_info()
        kernel_version = Uname('-v')
        hostid = get_first_line(
            logger=logger,
            command='hostid'
        )
        
        os = {
            'NAME': 'Solaris',
            'HOSTID': hostid,
            'FULL_NAME': info.get('fullname') if info else None,
            'VERSION': info.get('version') if info else None,
            'SERVICE_PACK': info.get('subversion') if info else None,
            'KERNEL_VERSION': kernel_version
        }
        
        usepkg = can_run('pkg')
        # Find installation date for any well-known core package
        for corepackage in ['SUNWcs', 'SUNWcsr', 'SUNWcsl', 'SUNWcsd', 'SUNWcslr', 'SUNWcsu']:
            installdate = OS._get_install_date(
                command=f"{'pkg info' if usepkg else 'pkginfo -l'} {corepackage}",
                usepkg=usepkg,
                logger=logger
            )
            if not empty(installdate):
                os['INSTALL_DATE'] = installdate
                break
        
        if inventory:
            inventory.set_operating_system(os)
    
    @staticmethod
    def _get_install_date(**params) -> Optional[str]:
        """Get package installation date."""
        try:
            import datetime as dt
        except ImportError:
            return None
        
        usepkg = params.pop('usepkg', False)
        
        if usepkg:
            # Format: Last Install Time: <day> <month> <day_num> HH:MM:SS <year>
            match = get_first_match(
                pattern=r'Last Install Time:\s+\S+\s+(\S+)\s+(\d+)\s+(\d+):(\d+):(\d+)\s+(\d+)$',
                **params
            )
        else:
            # Format: INSTDATE: <month> <day> <year> HH:MM
            match = get_first_match(
                pattern=r'INSTDATE:\s+(\S+)\s+(\d+)\s+(\d+)\s+(\d+):(\d+)$',
                **params
            )
        
        if not match:
            return None
        
        try:
            if usepkg:
                # match: (month_name, day, hour, minute, second, year)
                dt_obj = dt.datetime(
                    month=month(match[0]),
                    day=int(match[1]),
                    year=int(match[5]),
                    hour=int(match[2]),
                    minute=int(match[3]),
                    second=int(match[4])
                )
            else:
                # match: (month_name, day, year, hour, minute)
                dt_obj = dt.datetime(
                    month=month(match[0]),
                    day=int(match[1]),
                    year=int(match[2]),
                    hour=int(match[3]),
                    minute=int(match[4]),
                    second=0
                )
            return dt_obj.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError, IndexError):
            return None
