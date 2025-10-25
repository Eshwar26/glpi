#!/usr/bin/env python3
"""
GLPI Agent Hardware Qlogic Module - Python Implementation

Inventory module for Qlogic fibre channel switches.
Inventories fibre-channel ports.

Note: Qlogic switches are stackable but whichever switch you get SNMP data from
it is always stack member #1. So just get the data for the 1st member and
don't worry about the others.
"""

from typing import Dict, List, Optional, Any

# Import SNMP tools
try:
    from GLPI.Agent.Tools.SNMP import get_canonical_mac_address, get_canonical_serial_number
except ImportError:
    # Mock for standalone usage
    def get_canonical_mac_address(value):
        return value
    
    def get_canonical_serial_number(value):
        return value


__all__ = ['run']


def run(**params):
    """
    Run Qlogic-specific hardware inventory.
    
    Args:
        **params: Parameters including:
            - snmp: SNMP connection object
            - device: Device information dictionary
            - logger: Logger object
    """
    snmp = params.get('snmp')
    device = params.get('device')
    
    if not snmp or not device:
        return
    
    ports = device.get('PORTS', {}).get('PORT', {})
    if not ports:
        ports = {}
        if 'PORTS' not in device:
            device['PORTS'] = {}
        device['PORTS']['PORT'] = ports
    
    # Get device serial number
    serial = get_serial(snmp=snmp)
    if serial:
        if 'INFO' not in device:
            device['INFO'] = {}
        device['INFO']['SERIAL'] = serial
    
    # Get FC ports
    fc_ports = get_fc_ports(snmp=snmp)
    if not fc_ports:
        return
    
    # Get connected WWNs
    connected_wwns = get_connected_wwns(snmp=snmp)
    
    # Get port status
    port_status = get_fc_port_status(snmp=snmp)
    
    # Create port entries
    for idx, wwn in fc_ports.items():
        # Generate ifNumber for FC ports to avoid confusion with ethernet ports numbers
        port_id = int(f"10{idx:02d}00")
        
        ports[port_id] = {
            'IFNUMBER': port_id,
            'IFTYPE': 56,  # fibreChannel
            'IFNAME': f"FC port {idx}",
            'MAC': wwn,
            'IFSTATUS': port_status.get(idx) if port_status else None,
        }
        
        # Add connected WWNs if available
        if connected_wwns and idx in connected_wwns:
            ports[port_id]['CONNECTIONS'] = {
                'CONNECTION': {
                    'MAC': connected_wwns[idx]
                }
            }


def get_fc_ports(snmp) -> Optional[Dict[int, str]]:
    """
    Get Fibre Channel ports from SNMP.
    
    Args:
        snmp: SNMP connection object
        
    Returns:
        Dictionary mapping port index to WWN (MAC address)
    """
    if not snmp:
        return None
    
    fc_port = {}
    
    # Walk FIBRE-CHANNEL-FE-MIB::fcFxPortName
    fc_fx_port_name = snmp.walk(".1.3.6.1.2.1.75.1.1.5.1.2.1")
    
    if not fc_fx_port_name:
        return None
    
    # Example:
    # FIBRE-CHANNEL-FE-MIB::fcFxPortName.1.1 = Hex-STRING: 20 00 00 C0 DD 0C C5 27
    # FIBRE-CHANNEL-FE-MIB::fcFxPortName.1.2 = Hex-STRING: 20 01 00 C0 DD 0C C5 27
    for idx, wwn in fc_fx_port_name.items():
        wwn = get_canonical_mac_address(wwn)
        if not wwn:
            continue
        
        # Convert idx to integer if it's a string
        try:
            idx = int(idx) if isinstance(idx, str) else idx
        except ValueError:
            continue
        
        fc_port[idx] = wwn
    
    return fc_port if fc_port else None


def get_fc_port_status(snmp) -> Optional[Dict[int, int]]:
    """
    Get FC port operational status from SNMP.
    
    Args:
        snmp: SNMP connection object
        
    Returns:
        Dictionary mapping port index to operational status
    """
    if not snmp:
        return None
    
    # Walk FIBRE-CHANNEL-FE-MIB::fcFxPortPhysOperStatus
    fc_fx_port_phys_oper_status = snmp.walk(".1.3.6.1.2.1.75.1.2.2.1.2.1")
    
    return fc_fx_port_phys_oper_status


def get_connected_wwns(snmp) -> Optional[Dict[int, List[str]]]:
    """
    Get connected World Wide Names from SNMP.
    
    Args:
        snmp: SNMP connection object
        
    Returns:
        Dictionary mapping port index to list of WWNs
    """
    if not snmp:
        return None
    
    results = {}
    
    # Walk FIBRE-CHANNEL-FE-MIB::fcFxPortNxPortName
    fc_fx_port_nx_port_name = snmp.walk(".1.3.6.1.2.1.75.1.2.3.1.10.1")
    
    if not fc_fx_port_nx_port_name:
        return None
    
    # Example:
    # .1.3.6.1.2.1.75.1.2.3.1.10.1.1.1 = Hex-STRING: 21 00 00 24 FF 57 5D 9C
    # .1.3.6.1.2.1.75.1.2.3.1.10.1.2.1 = Hex-STRING: 21 00 00 24 FF 57 5F 18
    for suffix, wwn in fc_fx_port_nx_port_name.items():
        wwn = get_canonical_mac_address(wwn)
        if not wwn:
            continue
        
        # Extract index from suffix (first element)
        try:
            parts = suffix.split('.')
            if parts:
                idx = int(parts[0])
            else:
                continue
        except (ValueError, IndexError):
            continue
        
        if idx not in results:
            results[idx] = []
        results[idx].append(wwn)
    
    return results if results else None


def get_serial(snmp) -> Optional[str]:
    """
    Get device serial number from SNMP.
    
    Args:
        snmp: SNMP connection object
        
    Returns:
        Serial number string or None
    """
    if not snmp:
        return None
    
    # Walk vendor-specific OID for serial number
    walk = snmp.walk(".1.3.6.1.3.94.1.6.1.8.16.0.0.192.221.12")
    
    if walk:
        for suffix, serial in walk.items():
            if serial:
                return get_canonical_serial_number(serial)
    
    return None


if __name__ == '__main__':
    print("GLPI Agent Hardware Qlogic Module")
    print("Inventory module for Qlogic fibre channel switches")
