"""
GLPI Agent ToolBox Results OtherFields Module

Handles miscellaneous field definitions.
"""

from typing import Dict, Any, List

try:
    from GLPI.Agent.HTTP.Server.ToolBox.Results.Fields import Fields
except ImportError:
    Fields = object


class OtherFields(Fields if Fields != object else object):
    """
    Other fields result handler.
    
    Handles miscellaneous fields not covered by other sources.
    """

    def __init__(self, **params):
        """Initialize OtherFields result handler."""
        super().__init__(**params)

    def order(self) -> int:
        """Get processing order."""
        return 500

    def sections(self) -> List[Dict[str, Any]]:
        """
        Get field sections.
        
        Returns:
            List of section definitions
        """
        return [
            {
                'name': 'other',
                'index': 100,
                'title': 'Other Information'
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
                'name': 'comment',
                'section': 'other',
                'type': 'text',
                'text': 'Comment',
                'column': 100,
                'editcol': 2,
                'index': 1,
            },
            {
                'name': 'category',
                'section': 'other',
                'type': 'text',
                'text': 'Category',
                'column': 50,
                'editcol': 2,
                'index': 2,
            },
        ]

