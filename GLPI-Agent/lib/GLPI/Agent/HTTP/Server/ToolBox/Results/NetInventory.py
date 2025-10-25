"""
GLPI Agent ToolBox Results NetInventory Module

Handles network inventory result fields and analysis.
"""

from typing import Dict, Any, List

try:
    from GLPI.Agent.HTTP.Server.ToolBox.Results.Fields import Fields
except ImportError:
    Fields = object


class NetInventory(Fields if Fields != object else object):
    """
    Network inventory result handler.
    
    Defines fields for inventoried network devices.
    """

    def __init__(self, **params):
        """Initialize NetInventory result handler."""
        super().__init__(**params)

    def order(self) -> int:
        """Get processing order."""
        return 30

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
                'name': 'network',
                'index': 1,
                'title': 'Networking'
            },
            {
                'name': 'system',
                'index': 5,
                'title': 'System information'
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
                'from': ['NAME', 'IP'],
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
                'name': 'manufacturer',
                'section': 'system',
                'type': 'readonly',
                'from': 'MANUFACTURER',
                'text': 'Manufacturer',
                'column': 3,
                'editcol': 1,
                'index': 1,
            },
            {
                'name': 'model',
                'section': 'system',
                'type': 'readonly',
                'from': 'MODEL',
                'text': 'Model',
                'column': 3,
                'editcol': 1,
                'index': 2,
            },
            {
                'name': 'serial',
                'section': 'system',
                'type': 'readonly',
                'from': 'SERIAL',
                'text': 'Serial',
                'column': 4,
                'editcol': 1,
                'index': 3,
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

