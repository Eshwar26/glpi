# glpi_agent/task/inventory/generic/timezone.py

import platform
import time
from datetime import datetime, timezone
import calendar

from glpi_agent.task.inventory.module import InventoryModule
from glpi_agent.tools import can_run, get_all_lines


class Timezone(InventoryModule):
    """Generic Timezone inventory module."""
    
    @staticmethod
    def category():
        return "os"
    
    def is_enabled(self, **params):
        # No specific dependencies necessary
        return True
    
    def do_inventory(self, **params):
        inventory = params.get('inventory')
        logger = params.get('logger')
        remote = inventory.get_remote()
        
        # We should handle remote case
        if remote:
            try:
                from glpi_agent.tools import remote as remote_tools
                tz = remote_tools.remote_time_zone()
                if tz:
                    inventory.set_operating_system({'TIMEZONE': tz})
            except (ImportError, AttributeError):
                pass
            return
        
        # Compute a timezone offset like '+0200' using the difference between UTC and local time
        # Get the local time
        current_time = time.time()
        local_time = time.localtime(current_time)
        
        # Compute the time offset in seconds between local and UTC time
        utc_offset_seconds = calendar.timegm(local_time) - time.mktime(local_time)
        utc_offset_seconds_abs = abs(utc_offset_seconds)
        
        # Offset sign is minus if utc_offset_seconds is negative, plus otherwise
        offset_sign = '-' if utc_offset_seconds < 0 else '+'
        
        # Format the offset string: sign + H (XX) + M (XX)
        hours = int(utc_offset_seconds_abs // 3600)
        minutes = int((utc_offset_seconds_abs % 3600) // 60)
        tz_offset = f"{offset_sign}{hours:02d}{minutes:02d}"
        
        # Assume by default that the offset is empty (safe default in case something goes wrong below)
        tz_name = ''
        
        # Timezone name extraction will use one of the following sources:
        # * dateutil.tz => 'Europe/Paris'
        # * tzutil (Win 7+, Win 2008+) => 'Romance Standard Time'
        # * time.tzname => 'CEST'
        
        try:
            from dateutil import tz as dateutil_tz
            logger.debug("Using dateutil.tz to get the timezone name")
            local_tz = dateutil_tz.tzlocal()
            tz_name = str(local_tz)
            if tz_name.startswith('tzlocal()'):
                # Fallback if tzlocal() doesn't give a name
                tz_name = time.tzname[time.daylight]
        except ImportError:
            if platform.system() == 'Windows' or can_run('tzutil'):
                logger.debug("Using tzutil to get the timezone name")
                
                lines = get_all_lines(
                    logger=logger,
                    command='tzutil /g',
                )
                
                for line in lines:
                    tz_name = line.strip()
                    break
            
            elif platform.system() != 'Windows':
                logger.debug("Using time.tzname to get the timezone name")
                tz_name = time.tzname[time.daylight]
        
        inventory.set_operating_system({
            'TIMEZONE': {
                'NAME': tz_name,
                'OFFSET': tz_offset,
            }
        })