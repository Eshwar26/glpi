"""
GLPI Agent ToolBox Results Archive7z Module

7-Zip archive format handler.
"""

try:
    from GLPI.Agent.HTTP.Server.ToolBox.Results.Archive import Archive
except ImportError:
    Archive = object


class Archive7z(Archive if Archive != object else object):
    """
    7-Zip archive format handler.
    
    Handles 7z file creation and extraction.
    """

    def __init__(self, **params):
        """Initialize 7z archive handler."""
        super().__init__(**params)

    def format(self) -> str:
        """Get archive format."""
        return '7z'

    def order(self) -> int:
        """Get processing order."""
        return 30

