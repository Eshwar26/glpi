#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux Networks - Python Implementation
"""

import os
import re
from typing import Any, List, Dict, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, can_read, has_folder, has_file, get_first_line, get_all_lines, get_first_match, Glob
from GLPI.Agent.Tools.Network import (
    get_default_gateway_from_ip, get_routing_table, is_same_network,
    get_subnet_address, get_interfaces_from_ip, get_interfaces_from_ifconfig,
    get_interfaces_infos_from_ioctl, mac_address_pattern
)
from GLPI.Agent.Tools.Linux import get_ip_dhcp


class Networks(InventoryModule):
    """Linux network interface inventory module."""
    
    category = "network"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return True
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        default = get_default_gateway_from_ip(logger=logger)
        if not default:
            routes = get_routing_table(command='netstat -nr', logger=logger)
            default = routes.get('0.0.0.0') or routes.get('default')
        
        interfaces = Networks._get_interfaces(logger=logger)
        for interface in interfaces:
            # if the default gateway address and the interface address belongs to
            # the same network, that's the gateway for this network
            if is_same_network(
                default,
                interface.get('IPADDRESS'),
                interface.get('IPMASK')
            ):
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
        """Get all network interfaces with full information."""
        logger = params.get('logger')
        
        interfaces = Networks._get_interfaces_base(logger=logger)
        
        for interface in interfaces:
            interface['IPSUBNET'] = get_subnet_address(
                interface.get('IPADDRESS'),
                interface.get('IPMASK')
            )
            
            interface['IPDHCP'] = get_ip_dhcp(
                logger,
                interface.get('DESCRIPTION')
            )
            
            desc = interface.get('DESCRIPTION', '')
            
            # check if it is a physical interface
            if (has_folder(f"/sys/class/net/{desc}/device") and
                not has_folder(f"/sys/devices/virtual/net/{desc}")):
                
                info = Networks._get_uevent(desc)
                if info:
                    if info.get('DRIVER'):
                        interface['DRIVER'] = info['DRIVER']
                    if info.get('PCI_SLOT_NAME'):
                        interface['PCISLOT'] = info['PCI_SLOT_NAME']
                    if info.get('PCI_SUBSYS_ID') and info.get('PCI_ID'):
                        interface['PCIID'] = f"{info['PCI_ID']}:{info['PCI_SUBSYS_ID']}"
                
                interface['VIRTUALDEV'] = 0
                
                # check if it is a wifi interface, otherwise assume ethernet
                if has_folder(f"/sys/class/net/{desc}/wireless"):
                    interface['TYPE'] = 'wifi'
                    wifi_info = Networks._parse_iwconfig(name=desc)
                    if wifi_info:
                        if wifi_info.get('mode'):
                            interface['WIFI_MODE'] = wifi_info['mode']
                        if wifi_info.get('SSID'):
                            interface['WIFI_SSID'] = wifi_info['SSID']
                        if wifi_info.get('BSSID'):
                            interface['WIFI_BSSID'] = wifi_info['BSSID']
                        if wifi_info.get('version'):
                            interface['WIFI_VERSION'] = wifi_info['version']
                elif has_file(f"/sys/class/net/{desc}/mode"):
                    interface['TYPE'] = 'infiniband'
                else:
                    interface['TYPE'] = 'ethernet'
            else:
                interface['VIRTUALDEV'] = 1
                
                if desc == 'lo':
                    interface['TYPE'] = 'loopback'
                
                if desc.startswith('ppp'):
                    interface['TYPE'] = 'dialup'
                
                # check if it is an alias or a tagged interface
                alias_match = re.match(r'^([\w\d]+)[:.]\d+$', desc)
                if alias_match:
                    interface['TYPE'] = 'alias'
                    interface['BASE'] = alias_match.group(1)
                
                # check if it is a bridge
                if has_folder(f"/sys/class/net/{desc}/brif"):
                    interface['SLAVES'] = Networks._get_slaves(desc)
                    interface['TYPE'] = 'bridge'
                
                # check if it is a bonding master
                if has_folder(f"/sys/class/net/{desc}/bonding"):
                    interface['SLAVES'] = Networks._get_slaves(desc)
                    interface['TYPE'] = 'aggregate'
            
            # check if it is a bonding slave
            if has_folder(f"/sys/class/net/{desc}/bonding_slave"):
                mac = get_first_match(
                    command=f"ethtool -P {desc}",
                    pattern=rf'^Permanent address: ({mac_address_pattern})$',
                    logger=logger
                )
                if mac:
                    interface['MACADDR'] = mac
            
            if interface.get('STATUS') == 'Up':
                # Try to get speed from sysfs
                if can_read(f"/sys/class/net/{desc}/speed"):
                    speed = get_first_line(file=f"/sys/class/net/{desc}/speed")
                    if speed:
                        try:
                            speed_int = int(speed)
                            interface['SPEED'] = speed_int if speed_int > 0 else 0
                        except ValueError:
                            interface['SPEED'] = 0
                
                # Try wireless speed
                if not interface.get('SPEED') and has_folder(f"/sys/class/net/{desc}/wireless"):
                    speed = None
                    if can_run('iwconfig'):
                        speed = get_first_match(
                            command=f"iwconfig {desc}",
                            pattern=r'^\s+Bit Rate=(\d+)\s+Mb/s',
                            logger=logger
                        )
                    if not speed and can_run('nmcli'):
                        speed = get_first_match(
                            command=f"nmcli -c no -g DEVICE,ACTIVE,RATE dev wifi list ifname {desc}",
                            pattern=rf'^{re.escape(desc)}:yes:(\d+)\sMbit/s$',
                            logger=logger
                        )
                    if speed:
                        interface['SPEED'] = int(speed)
                
                # On older kernels, try ethtool system call for speed
                # but don't try this method on virtual dev
                if not interface.get('SPEED') and not interface.get('VIRTUALDEV'):
                    if logger:
                        logger.debug(f"looking for interface speed from syscall for {desc}:")
                    infos = get_interfaces_infos_from_ioctl(
                        interface=desc,
                        logger=logger
                    )
                    if infos and infos.get('SPEED'):
                        if logger:
                            logger.debug_result(
                                action='retrieving interface speed from syscall',
                                data=infos['SPEED']
                            )
                        interface['SPEED'] = infos['SPEED']
                    else:
                        if logger:
                            error = infos.get('ERROR', 'syscall failed') if infos else 'syscall failed'
                            logger.debug_result(
                                action='retrieving interface speed from syscall',
                                status=error
                            )
            else:
                # Report zero speed in case the interface went from up to down
                # or the server has non-zero interface speed
                interface['SPEED'] = 0
        
        return interfaces
    
    @staticmethod
    def _get_interfaces_base(**params) -> List[Dict[str, Any]]:
        """Get basic interface list using available commands."""
        logger = params.get('logger')
        if logger:
            logger.debug("retrieving interfaces list:")
        
        if can_run('/sbin/ip'):
            interfaces = get_interfaces_from_ip(logger=logger)
            if logger:
                logger.debug_result(
                    action='running /sbin/ip command',
                    data=len(interfaces)
                )
            if interfaces:
                return interfaces
        else:
            if logger:
                logger.debug_result(
                    action='running /sbin/ip command',
                    status='command not available'
                )
        
        if can_run('/sbin/ifconfig'):
            interfaces = get_interfaces_from_ifconfig(logger=logger)
            if logger:
                logger.debug_result(
                    action='running /sbin/ifconfig command',
                    data=len(interfaces)
                )
            if interfaces:
                return interfaces
        else:
            if logger:
                logger.debug_result(
                    action='running /sbin/ifconfig command',
                    status='command not available'
                )
        
        return []
    
    @staticmethod
    def _get_slaves(name: str) -> str:
        """Get slave interfaces for bonding/bridge."""
        slave_files = Glob(f"/sys/class/net/{name}/lower_*")
        slaves = []
        for path in slave_files:
            match = re.search(r'/lower_(\w+)$', path)
            if match:
                slaves.append(match.group(1))
        return ','.join(slaves)
    
    @staticmethod
    def _get_uevent(name: str) -> Optional[Dict[str, str]]:
        """Parse uevent file for device information."""
        file_path = f"/sys/class/net/{name}/device/uevent"
        lines = get_all_lines(file=file_path)
        if not lines:
            return None
        
        info = {}
        for line in lines:
            match = re.match(r'^(\w+)=(\S+)$', line)
            if match:
                info[match.group(1)] = match.group(2)
        
        return info
    
    @staticmethod
    def _parse_iwconfig(**params) -> Optional[Dict[str, str]]:
        """Parse iwconfig output for wireless information."""
        name = params.get('name')
        if name and 'command' not in params:
            params['command'] = f"iwconfig {name}"
        
        lines = get_all_lines(**params)
        if not lines:
            return None
        
        info = {}
        for line in lines:
            version_match = re.search(r'IEEE (\S+)', line)
            if version_match:
                info['version'] = version_match.group(1)
            
            ssid_match = re.search(r'ESSID:"([^"]+)"', line)
            if ssid_match:
                info['SSID'] = ssid_match.group(1)
            
            mode_match = re.search(r'Mode:(\S+)', line)
            if mode_match:
                info['mode'] = mode_match.group(1)
            
            bssid_match = re.search(rf'Access Point: ({mac_address_pattern})', line)
            if bssid_match:
                info['BSSID'] = bssid_match.group(1)
        
        return info
