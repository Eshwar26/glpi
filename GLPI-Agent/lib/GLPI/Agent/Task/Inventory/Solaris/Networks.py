#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Solaris Networks - Python Implementation
"""

import re
from typing import Any, List, Dict, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines, get_first_match
from GLPI.Agent.Tools.Unix import get_routing_table
from GLPI.Agent.Tools.Network import (is_same_network, get_subnet_address, get_network_mask_ipv6,
                                      hex2canonical, get_canonical_interface_speed, ip_address_pattern,
                                      hex_ip_address_pattern)


class Networks(InventoryModule):
    """Solaris network interfaces detection module."""
    
    category = "network"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('ifconfig')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        routes = get_routing_table(logger=logger)
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
        
        interfaces = Networks._parse_ifconfig(
            command='ifconfig -a',
            **params
        )
        
        has_dladm = can_run('/usr/sbin/dladm')
        
        for interface in interfaces:
            if interface.get('IPADDRESS') and interface.get('IPMASK'):
                interface['IPSUBNET'] = get_subnet_address(
                    interface['IPADDRESS'],
                    interface['IPMASK']
                )
            
            name = interface.get('DESCRIPTION')
            if not name:
                continue
            
            speed = None
            if has_dladm:
                speed = Networks._get_interface_speed_via_dladm(
                    logger=logger,
                    name=name
                )
            else:
                speed = Networks._get_interface_speed(
                    logger=logger,
                    name=name
                )
            if speed:
                interface['SPEED'] = speed
        
        if has_dladm:
            interfaces.extend(Networks._parse_dladm(
                command='/usr/sbin/dladm show-aggr',
                logger=logger
            ))
        
        if can_run('/usr/sbin/fcinfo'):
            interfaces.extend(Networks._parse_fcinfo(
                command='/usr/sbin/fcinfo hba-port',
                logger=logger
            ))
        
        return interfaces
    
    @staticmethod
    def _get_interface_speed_via_dladm(**params) -> Optional[int]:
        """Get interface speed via dladm."""
        name = params.get('name')
        if not name:
            return None
        
        return get_first_match(
            command=f'/usr/sbin/dladm show-phys {name}',
            pattern=rf'^{re.escape(name)}\s+\S+\s+\S+\s+(\d+)\s+',
            **params
        )
    
    @staticmethod
    def _get_interface_speed(**params) -> Optional[int]:
        """Get interface speed via kstat."""
        name = params.get('name')
        if not name:
            return None
        
        match = re.match(r'^(\S+?)(\d+)', name)
        if not match:
            return None
        
        iface_type = match.group(1)
        instance = match.group(2)
        
        if iface_type in ['aggr', 'dmfe']:
            return None
        
        command = f'/usr/bin/kstat -m {iface_type} -i {instance} -s link_speed'
        
        speed = get_first_match(
            **params,
            command=command,
            pattern=r'^\s*link_speed+\s*(\d+)'
        )
        
        # By default, kstat reports speed as Mb/s, no need to normalize
        return speed
    
    @staticmethod
    def _parse_ifconfig(**params) -> List[Dict[str, Any]]:
        """Parse ifconfig output."""
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        interfaces = []
        interface = None
        
        for line in lines:
            # Check for interface with sub-interface (e.g., ce0:1)
            match = re.match(r'^(\S+):(\S+):', line)
            if match:
                # new interface
                if interface:
                    interfaces.append(interface)
                # quick assertion: nothing else as ethernet interface
                interface = {
                    'STATUS': 'Down',
                    'DESCRIPTION': f"{match.group(1)}:{match.group(2)}",
                    'TYPE': 'ethernet'
                }
                continue
            
            # Check for interface (e.g., ce0)
            match = re.match(r'^(\S+):', line)
            if match:
                # new interface
                if interface:
                    interfaces.append(interface)
                # quick assertion: nothing else as ethernet interface
                interface = {
                    'STATUS': 'Down',
                    'DESCRIPTION': match.group(1),
                    'TYPE': 'ethernet'
                }
                continue
            
            if not interface:
                continue
            
            # Parse inet address
            inet_match = re.search(rf'inet ({ip_address_pattern})', line)
            if inet_match:
                interface['IPADDRESS'] = inet_match.group(1)
            
            # Parse inet6 address
            inet6_match = re.match(r'inet6 (\S+)/(\d+)', line)
            if inet6_match:
                interface['IPADDRESS6'] = inet6_match.group(1)
                interface['IPMASK6'] = get_network_mask_ipv6(int(inet6_match.group(2)))
            
            # Parse netmask
            netmask_match = re.search(rf'netmask ({hex_ip_address_pattern})', line, re.IGNORECASE)
            if netmask_match:
                interface['IPMASK'] = hex2canonical(netmask_match.group(1))
            
            # Parse MAC address
            ether_match = re.search(r'ether\s+(\S+)', line, re.IGNORECASE)
            if ether_match:
                # Format MAC address properly
                mac_parts = ether_match.group(1).split(':')
                interface['MACADDR'] = ':'.join(f'{int(part, 16):02x}' for part in mac_parts)
            
            # Check status
            if '<UP,' in line:
                interface['STATUS'] = 'Up'
        
        # last interface
        if interface:
            interfaces.append(interface)
        
        return interfaces
    
    @staticmethod
    def _parse_dladm(**params) -> List[Dict[str, Any]]:
        """Parse dladm output for aggregations."""
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        interfaces = []
        for line in lines:
            if 'device' in line or 'key' in line:
                continue
            
            match = re.match(r'(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)', line)
            if not match:
                continue
            
            interface = {
                'STATUS': 'Down',
                'IPADDRESS': '0.0.0.0',
                'DESCRIPTION': match.group(1),
                'MACADDR': match.group(2),
                'SPEED': get_canonical_interface_speed(match.group(3) + match.group(4)),
            }
            
            if 'UP' in line:
                interface['STATUS'] = 'Up'
            
            interfaces.append(interface)
        
        return interfaces
    
    @staticmethod
    def _parse_fcinfo(**params) -> List[Dict[str, Any]]:
        """Parse fcinfo output for Fibre Channel interfaces."""
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        interfaces = []
        inc = 1
        interface = {}
        
        for line in lines:
            wwn_match = re.search(r'HBA Port WWN:\s+(\S+)', line)
            if wwn_match:
                interface['DESCRIPTION'] = f"HBA_Port_WWN_{inc}"
            
            dev_match = re.search(r'OS Device Name:\s+(\S+)', line)
            if dev_match:
                interface['DESCRIPTION'] = interface.get('DESCRIPTION', '') + f" {dev_match.group(1)}"
            
            speed_match = re.search(r'Current Speed:\s+(\S+)', line)
            if speed_match:
                interface['SPEED'] = get_canonical_interface_speed(speed_match.group(1))
            
            node_wwn_match = re.search(r'Node WWN:\s+(\S+)', line)
            if node_wwn_match:
                interface['WWN'] = node_wwn_match.group(1)
            
            driver_match = re.search(r'Driver Name:\s+(\S+)', line, re.IGNORECASE)
            if driver_match:
                interface['DRIVER'] = driver_match.group(1)
            
            mfr_match = re.search(r'Manufacturer:\s+(.*)$', line)
            if mfr_match:
                interface['MANUFACTURER'] = mfr_match.group(1)
            
            model_match = re.search(r'Model:\s+(.*)$', line)
            if model_match:
                interface['MODEL'] = model_match.group(1)
            
            fw_match = re.search(r'Firmware Version:\s+(.*)$', line)
            if fw_match:
                interface['FIRMWARE'] = fw_match.group(1)
            
            if 'online' in line:
                interface['STATUS'] = 'Up'
            
            if interface.get('DESCRIPTION') and interface.get('WWN'):
                interface['TYPE'] = 'fibrechannel'
                if not interface.get('STATUS'):
                    interface['STATUS'] = 'Down'
                
                interfaces.append(interface)
                interface = {}
                inc += 1
        
        return interfaces
