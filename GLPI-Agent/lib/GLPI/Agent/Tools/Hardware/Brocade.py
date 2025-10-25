#!/usr/bin/env python3
"""
GLPI Agent Hardware Brocade Module - Python Implementation

Inventory module for Brocade fibre channel switches.
Inventories fibre-channel ports.
"""

from typing import Dict, List, Optional, Any

# Import SNMP tools
try:
    from GLPI.Agent.Tools.SNMP import get_canonical_mac_address
except ImportError:
    # Mock for standalone usage
    def get_canonical_mac_address(value):
        return value


__all__ = ['run']


def run(**params):
    """
    Run Brocade-specific hardware inventory.
    
    Args:
        **params: Parameters including:
            - snmp: SNMP connection object
            - device: Device information dictionary
            - logger: Logger object
    """
    snmp = params.get('snmp')
    device = params.get('device')
    logger = params.get('logger')
    
    if not snmp or not device:
        return
    
    ports = device.get('PORTS', {}).get('PORT', {})
    if not ports:
        return
    
    # Get connected WWNs (World Wide Names)
    wwns = get_connected_wwns(snmp=snmp)
    if not wwns:
        return
    
    # Get FC port mapping
    fc_ports = get_fc_ports(ports)
    if not fc_ports:
        return
    
    # Associate WWNs with ports
    for idx, wwn_list in wwns.items():
        if idx not in fc_ports:
            if logger:
                logger.error(f"non-existing FC port {idx}")
            continue
        
        port_id = fc_ports[idx]
        if port_id not in ports:
            if logger:
                logger.error(f"non-existing FC port {idx}")
            continue
        
        port = ports[port_id]
        
        # Initialize CONNECTIONS structure if needed
        if 'CONNECTIONS' not in port:
            port['CONNECTIONS'] = {}
        if 'CONNECTION' not in port['CONNECTIONS']:
            port['CONNECTIONS']['CONNECTION'] = {}
        if 'MAC' not in port['CONNECTIONS']['CONNECTION']:
            port['CONNECTIONS']['CONNECTION']['MAC'] = []
        
        # Add WWNs to port connections
        port['CONNECTIONS']['CONNECTION']['MAC'].extend(wwn_list)


def get_fc_ports(ports: Dict[int, Dict]) -> Dict[int, int]:
    """
    Map IFMIB ports to FIBRE-CHANNEL-FE-MIB ports.
    
    Args:
        ports: Dictionary of port information
        
    Returns:
        Dictionary mapping FC port index to interface ID
    """
    fc_port = {}
    
    # FC ports count from 1
    i = 1
    for idx in sorted(ports.keys()):
        # Check if port type is fibreChannel (56)
        if ports[idx].get('IFTYPE') == 56:
            fc_port[i] = idx
            i += 1
    
    return fc_port


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
    fc_fx_port_nx_port_name = snmp.walk(".1.3.6.1.2.1.75.1.2.3.1.10")
    
    if not fc_fx_port_nx_port_name:
        return None
    
    # Example:
    # .1.3.6.1.2.1.75.1.2.3.1.10.1.1.1 = Hex-STRING: 21 00 00 24 FF 57 5D 9C
    # .1.3.6.1.2.1.75.1.2.3.1.10.1.2.1 = Hex-STRING: 21 00 00 24 FF 57 5F 18
    #                              ^--- $idx
    for suffix, wwn in fc_fx_port_nx_port_name.items():
        wwn = get_canonical_mac_address(wwn)
        if not wwn:
            continue
        
        # Extract index from suffix (second element)
        # Need to import _getElement from Hardware tools
        try:
            parts = suffix.split('.')
            if len(parts) >= 2:
                idx = int(parts[1])
            else:
                continue
        except (ValueError, IndexError):
            continue
        
        if idx not in results:
            results[idx] = []
        results[idx].append(wwn)
    
    return results if results else None


if __name__ == '__main__':
    print("GLPI Agent Hardware Brocade Module")
    print("Inventory module for Brocade fibre channel switches")
