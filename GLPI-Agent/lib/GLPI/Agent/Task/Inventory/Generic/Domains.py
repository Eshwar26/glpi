# glpi_agent/task/inventory/generic/domains.py

from glpi_agent.task.inventory.module import InventoryModule
from glpi_agent.tools import can_read, get_all_lines, empty
from glpi_agent.tools.hostname import get_hostname


class Domains(InventoryModule):
    """Generic Domains inventory module."""
    
    @staticmethod
    def category():
        return "hardware"
    
    def is_enabled(self, **params):
        return can_read("/etc/resolv.conf")
    
    def do_inventory(self, **params):
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        infos = {}
        
        # first, parse /etc/resolv.conf for the DNS servers,
        # and the domain search list
        search_list = {}
        lines = get_all_lines(
            file='/etc/resolv.conf',
            logger=logger
        )
        
        if lines:
            dns_list = {}
            for line in lines:
                import re
                
                # Check for nameserver
                match = re.match(r'^nameserver\s+(\S+)', line)
                if match:
                    dns = match.group(1).rstrip('.')
                    dns_list[dns] = 1
                else:
                    # Check for domain or search
                    match = re.match(r'^(?:domain|search)\s+(\S+)', line)
                    if match:
                        domain = match.group(1).rstrip('.')
                        search_list[domain] = 1
            
            if dns_list:
                infos['DNS'] = '/'.join(sorted(dns_list.keys()))
        
        # attempt to deduce the actual domain from the host name
        # and fallback on the domain search list
        hostname = get_hostname(fqdn=True)
        pos = 0 if empty(hostname) else hostname.find('.')
        
        if pos > 0:
            hostname = hostname.rstrip('.')
            if pos < len(hostname):
                infos['WORKGROUP'] = hostname[pos + 1:]
        
        if not infos.get('WORKGROUP') and search_list:
            infos['WORKGROUP'] = '/'.join(sorted(search_list.keys()))
        
        if infos:
            inventory.set_hardware(infos)