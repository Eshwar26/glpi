"""
GLPI Agent Task Inventory BSD Module

Platform module for BSD systems (FreeBSD, OpenBSD, NetBSD, DragonFly).
"""

import platform


class BSD:
    """BSD platform inventory module"""
    
    run_after = ["GLPI.Agent.Task.Inventory.Generic"]
    
    @staticmethod
    def is_enabled() -> bool:
        """Check if module is enabled (BSD variants only)"""
        system = platform.system().lower()
        return system in ['freebsd', 'openbsd', 'netbsd', 'dragonfly']
    
    @staticmethod
    def do_inventory(**params) -> None:
        """Execute the inventory (placeholder)"""
        pass
