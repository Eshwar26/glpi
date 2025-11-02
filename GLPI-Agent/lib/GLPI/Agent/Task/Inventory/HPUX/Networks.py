#!/usr/bin/env python3
"""
GLPI Agent Task Inventory HPUX Networks - Python Implementation
"""

import re
from typing import Any, List, Dict, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines
from GLPI.Agent.Tools.Unix import get_routing_table
from GLPI.Agent.Tools.Network import is_same_network, get_subnet_address, alt2canonical, hex2canonical, alt_mac_address_pattern, ip_address_pattern, hex_ip_address_pattern


class Networks(InventoryModule):
    """HP-UX network interfaces detection module."""
    
    category = "network"
    
    # TODO: Get pcislot, virtualdev
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('lanscan')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        routes = get_routing_table(command='netstat -nr', logger=logger)
        default = routes.get('0.0.0.0') or routes.get('default')
        
        interfaces = Networks._get_interfaces(logger=logger)
        for interface in interfaces:
            # if the default gateway address and the interface address belongs to
            # the same network, that's the gateway for this network
            if default and interface.get('IPADDRESS') and interface.get('IPMASK'):
                if is_same_network(default, interface['IPADDRESS'], interface['IPMASK']):
                    interface['IPGATEWAY'] = default
            
            if inventory:
                inventory.add_entry(
                    section='NETWORKS',
                    entry=interface
                )
        
        if inventory:
            inventory.set_hardware({
                'DEFAULTGATEWAY': default
            })
    
    @staticmethod
    def _get_interfaces(**params) -> List[Dict[str, Any]]:
        """Get network interfaces."""
        logger = params.get('logger')
        
        prototypes = Networks._parse_lanscan(
            command='lanscan -iap',
            logger=logger
        )
        
        if_stat_nrv = Networks._parse_netstat_nrv()
        
        interfaces = []
        for prototype in prototypes:
            lanadmin_info = Networks._get_lanadmin_info(
                command=f"lanadmin -g {prototype['lan_id']}",
                logger=logger
            )
            if lanadmin_info:
                prototype['TYPE'] = lanadmin_info.get('Type (value)')
                speed = lanadmin_info.get('Speed')
                if speed:
                    try:
                        speed_val = int(speed)
                        prototype['SPEED'] = speed_val / 1000000 if speed_val > 1000000 else speed_val
                    except (ValueError, TypeError):
                        pass
            
            if prototype['DESCRIPTION'] in if_stat_nrv:
                # if this interface name has been found in netstat output, let's
                # use the list of interfaces found there, using the prototype
                # to provide additional information
                for interface in if_stat_nrv[prototype['DESCRIPTION']]:
                    for key in ['MACADDR', 'STATUS', 'TYPE', 'SPEED']:
                        if prototype.get(key):
                            interface[key] = prototype[key]
                    interfaces.append(interface)
            else:
                # otherwise, we promote this prototype to an interface, using
                # ifconfig to provide additional information
                ifconfig_info = Networks._get_ifconfig_info(
                    command=f"ifconfig {prototype['DESCRIPTION']}",
                    logger=logger
                )
                if ifconfig_info:
                    prototype['STATUS'] = ifconfig_info.get('status')
                    prototype['IPADDRESS'] = ifconfig_info.get('address')
                    prototype['IPMASK'] = ifconfig_info.get('netmask')
                del prototype['lan_id']
                interfaces.append(prototype)
        
        for interface in interfaces:
            if interface.get('IPADDRESS') == '0.0.0.0':
                interface['IPADDRESS'] = None
                interface['IPMASK'] = None
            elif interface.get('IPADDRESS') and interface.get('IPMASK'):
                interface['IPSUBNET'] = get_subnet_address(
                    interface['IPADDRESS'],
                    interface['IPMASK']
                )
        
        return interfaces
    
    @staticmethod
    def _parse_lanscan(**params) -> List[Dict[str, Any]]:
        """Parse lanscan output."""
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        interfaces = []
        for line in lines:
            match = re.match(
                rf'^0x({alt_mac_address_pattern})\s+(\S+)\s+\S+\s+(\S+)',
                line
            )
            if match:
                # quick assertion: nothing else as ethernet interface
                interface = {
                    'MACADDR': alt2canonical(match.group(1)),
                    'STATUS': 'Down',
                    'DESCRIPTION': match.group(2),
                    'TYPE': 'ethernet',
                    'lan_id': match.group(3),
                }
                interfaces.append(interface)
        
        return interfaces
    
    @staticmethod
    def _get_lanadmin_info(**params) -> Optional[Dict[str, str]]:
        """Parse lanadmin output."""
        lines = get_all_lines(**params)
        if not lines:
            return None
        
        info = {}
        for line in lines:
            match = re.match(r'^(\S.+\S) \s+ = \s (.+)$', line, re.VERBOSE)
            if match:
                info[match.group(1)] = match.group(2)
        
        return info
    
    @staticmethod
    def _get_ifconfig_info(**params) -> Optional[Dict[str, str]]:
        """Parse ifconfig output."""
        lines = get_all_lines(**params)
        if not lines:
            return None
        
        info = {}
        for line in lines:
            if '<UP' in line:
                info['status'] = 'Up'
            
            addr_match = re.search(rf'inet ({ip_address_pattern})', line)
            if addr_match:
                info['address'] = addr_match.group(1)
            
            mask_match = re.search(rf'netmask ({hex_ip_address_pattern})', line)
            if mask_match:
                info['netmask'] = hex2canonical(mask_match.group(1))
        
        return info
    
    @staticmethod
    def _get_nwmgr_info(**params) -> Optional[Dict[str, Dict[str, Any]]]:
        """Parse nwmgr output - will be needed to get the bonding configuration."""
        lines = get_all_lines(**params)
        if not lines:
            return None
        
        info = {}
        for line in lines:
            match = re.match(
                rf'^(\w+)\s+(\w+)\s+0x({alt_mac_address_pattern})\s+(\w+)\s+(\w*)',
                line
            )
            if match:
                interface = match.group(1)
                info[interface] = {
                    'status': match.group(2),
                    'mac': alt2canonical(match.group(3)),
                    'driver': match.group(4),
                    'media': match.group(5),
                    'related_if': None
                }
        
        return info
    
    @staticmethod
    def _parse_netstat_nrv(**params) -> Dict[str, List[Dict[str, Any]]]:
        """Parse netstat -nrv output."""
        if 'command' not in params:
            params['command'] = 'netstat -nrv'
        
        lines = get_all_lines(**params)
        if not lines:
            return {}
        
        interfaces = {}
        for line in lines:
            match = re.match(
                rf'^({ip_address_pattern})\/'  # address
                rf'({ip_address_pattern})\s+'  # mask
                rf'({ip_address_pattern})\s+'  # gateway
                rf'[A-Z]* H [A-Z]*\s+'         # host flag
                rf'\d\s+'
                rf'(\w+)(?: :\d+)?\s+'         # interface name, with optional alias
                rf'(\d+)$',                     # MTU
                line
            )
            if match:
                address = match.group(1)
                mask = match.group(2)
                gateway = match.group(3) if match.group(3) != address else None
                interface = match.group(4)
                mtu = match.group(5)
                
                # quick assertion: nothing else as ethernet interface
                if interface not in interfaces:
                    interfaces[interface] = []
                
                interfaces[interface].append({
                    'IPADDRESS': address,
                    'IPMASK': mask,
                    'IPGATEWAY': gateway,
                    'DESCRIPTION': interface,
                    'TYPE': 'ethernet',
                    'MTU': mtu
                })
        
        return interfaces
