"""
GLPI Agent SNMP MibSupport for Ubiquiti (Ubnt / UniFi) devices

This module provides inventory support for Ubnt/UniFi devices via SNMP.
It extracts firmware version, model, MAC/serial and maps radio interfaces
(raX, raiX) to SSIDs (with 2.4GHz/5GHz labels), converting WiFi IFTYPE
from Ethernet (6) to WiFi (71) when appropriate.

See: UBNT-MIB, UBNT-UniFi-MIB
"""

import re
from typing import Optional, Dict, Any, List
from glpi_agent.snmp.mib_support_template import MibSupportTemplate
from glpi_agent.tools import Tools
from glpi_agent.tools.snmp import SNMPTools


class UbntMibSupport(MibSupportTemplate):
    """
    Inventory module for Ubiquiti Ubnt / UniFi devices.
    """

    # UBNT enterprise OID
    UBNT = '.1.3.6.1.4.1.41112'
    UBNT_WL_STAT_AP_MAC = f'{UBNT}.1.4.5.1.4.1'

    # UniFi related OIDs (UBNT-UniFi-MIB)
    UNIFI_VAP_ESSID = f'{UBNT}.1.6.1.2.1.6'
    UNIFI_VAP_NAME = f'{UBNT}.1.6.1.2.1.7'
    UNIFI_AP_SYSTEM_VERSION = f'{UBNT}.1.6.3.6.0'
    UNIFI_AP_SYSTEM_MODEL = f'{UBNT}.1.6.3.3.0'

    def __init__(self, **params):
        super().__init__(**params)
        self._sysobjectid = None

    @classmethod
    def get_mib_support(cls) -> List[Dict[str, Any]]:
        """
        Returns MIB support configuration for Ubnt devices.
        """
        return [
            {'name': 'ubnt', 'oid': cls.UBNT},
            {'name': 'ubnt-unifi', 'sysobjectid': SNMPTools.get_regexp_oid_match(cls.UBNT)}
        ]

    def getFirmware(self) -> Optional[str]:
        """
        Retrieve firmware/version string from UniFi AP OID.
        """
        ver = self.get(self.UNIFI_AP_SYSTEM_VERSION)
        return Tools.get_canonical_string(ver) if ver is not None else None

    def getModel(self) -> Optional[str]:
        """
        Retrieve device model from UniFi AP OID.
        """
        model = self.get(self.UNIFI_AP_SYSTEM_MODEL)
        return Tools.get_canonical_string(model) if model is not None else None

    def getSerial(self) -> Optional[str]:
        """
        Get a serial number. Attempts to use wireless-station AP MAC (UBNT specific)
        or falls back to the device 'MAC' field. Removes ':' to match Perl behavior.
        """
        device = self.device
        if not device:
            return None

        mac_val = self.get(self.UBNT_WL_STAT_AP_MAC)
        serial = Tools.get_canonical_mac_address(mac_val) if mac_val is not None else device.get('MAC')
        if not serial:
            return None

        # Remove colons to match original behavior (s/://g)
        return serial.replace(':', '')

    def getMacAddress(self) -> Optional[str]:
        """
        Return canonical MAC address from UBNT WL stat AP MAC OID.
        """
        mac_val = self.get(self.UBNT_WL_STAT_AP_MAC)
        return Tools.get_canonical_mac_address(mac_val) if mac_val is not None else None

    def run(self) -> None:
        """
        Post-processing to annotate radio ports with SSID names and frequency labels.

        - Walks UniFi VAP ESSID and VAP Name tables.
        - For each device port whose IFDESCR starts with 'ra' or 'rai', tries to
          match the radio name and set IFALIAS and IFNAME (SSID + (2.4GHz)/(5GHz)).
        - If a radio's IFTYPE is set to Ethernet (6) it will be changed to WiFi (71).
        """
        device = self.device
        if not device:
            return

        ports = device.get('PORTS', {}).get('PORT', {})
        if not isinstance(ports, dict):
            return

        unifi_vap_essid_values = self.walk(self.UNIFI_VAP_ESSID) or {}
        unifi_vap_name_values = self.walk(self.UNIFI_VAP_NAME) or {}

        # keys in walk results might be integers or strings - iterate their string forms
        for port_key in list(ports.keys()):
            port = ports.get(port_key)
            if not isinstance(port, dict):
                continue

            ifdescr = port.get('IFDESCR')
            if not ifdescr or not re.match(r'^ra', str(ifdescr)):
                continue

            # Convert ethernet iftype (6) to wifi (71) if present
            if 'IFTYPE' in port and port.get('IFTYPE') == 6:
                port['IFTYPE'] = 71

            # Find matching radio in unifi_vap_name_values
            for index, radio_name in unifi_vap_name_values.items():
                # Radio names and ifdescr should match exactly
                if str(ifdescr) == Tools.get_canonical_string(radio_name):
                    # Set IFALIAS to radio name
                    port['IFALIAS'] = str(ifdescr)

                    # Replace interface name with SSID (ESSID) if available
                    essid = Tools.get_canonical_string(unifi_vap_essid_values.get(index, ''))
                    if essid and not Tools.is_empty(essid):
                        if re.match(r'^ra\d+$', str(ifdescr)):
                            essid_with_freq = f"{essid} (2.4GHz)"
                        elif re.match(r'^rai\d+$', str(ifdescr)):
                            essid_with_freq = f"{essid} (5GHz)"
                        else:
                            essid_with_freq = essid

                        port['IFNAME'] = essid_with_freq

                    break


# Module-level variable for backward compatibility (similar to Perl's $mibSupport)
mib_support = UbntMibSupport.get_mib_support()

# Module metadata
__all__ = ['UbntMibSupport', 'mib_support']
__version__ = '1.0.0'
__author__ = 'GLPI Agent'
__description__ = 'Inventory module for Ubnt / UniFi network devices'
