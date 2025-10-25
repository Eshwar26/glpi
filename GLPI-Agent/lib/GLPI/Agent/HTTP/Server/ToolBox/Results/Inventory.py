"""
GLPI Agent ToolBox Results Inventory Module

Handles computer inventory result fields and analysis.
"""

from typing import Dict, Any, List

try:
    from GLPI.Agent.HTTP.Server.ToolBox.Results.Fields import Fields
except ImportError:
    Fields = object


class Inventory(Fields if Fields != object else object):
    """
    Computer inventory result handler.
    
    Defines fields for inventoried computers.
    """

    def __init__(self, **params):
        """Initialize Inventory result handler."""
        super().__init__(**params)

    def order(self) -> int:
        """Get processing order."""
        return 10

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
            },
            {
                'name': 'hardware',
                'index': 1,
                'title': 'Hardware'
            },
            {
                'name': 'network',
                'index': 2,
                'title': 'Network'
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
                'from': ['NAME', 'HOSTNAME'],
                'text': 'Computer name',
                'column': 0,
                'editcol': 0,
                'index': 0,
                'noedit': True,
            },
            {
                'name': 'manufacturer',
                'section': 'hardware',
                'type': 'readonly',
                'from': 'SMANUFACTURER',
                'text': 'Manufacturer',
                'column': 2,
                'editcol': 1,
                'index': 1,
            },
            {
                'name': 'model',
                'section': 'hardware',
                'type': 'readonly',
                'from': 'SMODEL',
                'text': 'Model',
                'column': 2,
                'editcol': 1,
                'index': 2,
            },
            {
                'name': 'serial',
                'section': 'hardware',
                'type': 'readonly',
                'from': 'SSN',
                'text': 'Serial',
                'column': 3,
                'editcol': 1,
                'index': 3,
            },
            {
                'name': 'uuid',
                'section': 'hardware',
                'type': 'readonly',
                'from': 'UUID',
                'text': 'UUID',
                'column': 10,
                'editcol': 1,
                'index': 4,
            },
            {
                'name': 'ip',
                'section': 'network',
                'type': 'readonly',
                'text': 'IP',
                'column': 1,
                'editcol': 0,
                'index': 1,
                'tosort': lambda value: self.sortable_by_ip(value),
            },
            {
                'name': 'mac',
                'section': 'network',
                'type': 'readonly',
                'text': 'MAC',
                'column': 1,
                'editcol': 1,
                'index': 2,
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

