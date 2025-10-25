"""
GLPI Agent ToolBox Results NetDiscovery Module

Handles network discovery result fields and analysis.
"""

from typing import Dict, Any, List
from functools import lru_cache

try:
    from GLPI.Agent.HTTP.Server.ToolBox.Results.Fields import Fields
except ImportError:
    Fields = object


class NetDiscovery(Fields if Fields != object else object):
    """
    Network discovery result handler.
    
    Defines fields for discovered network devices.
    """

    def __init__(self, **params):
        """Initialize NetDiscovery result handler."""
        super().__init__(**params)

    def order(self) -> int:
        """Get processing order."""
        return 20

    def sections(self) -> List[Dict[str, Any]]:
        """
        Get field sections.
        
        Returns:
            List of section definitions
        """
        return [
            {
                'name': 'default',
                'index': 0,
                # No title will be shown if title is not set
            },
            {
                'name': 'network',
                'index': 1,
                'title': 'Networking'
            },
            {
                'name': 'netscan',
                'index': 10,
                'title': 'Networking scan datas'
            }
        ]

    def fields(self) -> List[Dict[str, Any]]:
        """
        Get field definitions.
        
        Returns:
            List of field definitions
        """
        return [
            {
                'name': 'name',
                'section': 'default',
                'type': 'readonly',
                'from': ['SNMPHOSTNAME', 'DNSHOSTNAME', 'IP'],
                'text': 'Device name or IP',
                'column': 0,
                'editcol': 0,
                'index': 0,
                'noedit': True,
            },
            {
                'name': 'ip',
                'section': 'network',
                'type': 'readonly',
                'from': 'IP',
                'text': 'IP',
                'column': 1,
                'editcol': 0,
                'index': 1,
                'tosort': lambda value: self.sortable_by_ip(value),
                'noedit': True,
            },
            {
                'name': 'ips',
                'section': 'network',
                'type': 'readonly',
                'text': 'IPs',
                'column': 9,
                'editcol': 0,
                'index': 2,
            },
            {
                'name': 'mac',
                'section': 'network',
                'type': 'readonly',
                'from': 'MAC',
                'text': 'MAC',
                'column': 1,
                'editcol': 1,
                'index': 2,
            },
            {
                'name': 'serial',
                'section': 'default',
                'type': 'readonly',
                'from': 'SERIAL',
                'text': 'SerialNumber',
                'column': 4,
                'editcol': 1,
                'index': 1,
            },
            {
                'name': 'description',
                'section': 'default',
                'type': 'readonly',
                'from': 'DESCRIPTION',
                'text': 'Description',
                'column': 100,
                'editcol': 0,
                'index': 10,
            },
            {
                'name': 'location',
                'section': 'default',
                'type': 'readonly',
                'from': 'LOCATION',
                'text': 'Location',
                'column': 10,
                'editcol': 0,
                'index': 6,
            },
            {
                'name': 'type',
                'section': 'default',
                'type': 'readonly',
                'from': 'TYPE',
                'text': 'Type',
                'column': 1,
                'editcol': 1,
                'index': 0,
            },
            {
                'name': 'contact',
                'section': 'default',
                'type': 'readonly',
                'from': 'CONTACT',
                'text': 'Contact',
                'column': 1,
                'editcol': 1,
                'index': 30,
            },
            {
                'name': 'tag',
                'section': 'default',
                'type': 'readonly',
                'text': 'Tag',
                'column': 20,
                'editcol': 0,
                'index': 20,
                'noedit': True,
            },
            {
                'name': 'source',
                'section': 'default',
                'type': 'readonly',
                'text': 'Source',
                'column': 10,
                'editcol': 0,
                'index': 100,
                'noedit': True,
            },
        ]

