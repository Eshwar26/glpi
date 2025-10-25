"""
GLPI Agent ToolBox Results ArchiveZip Module

ZIP archive format handler.
"""

try:
    from GLPI.Agent.HTTP.Server.ToolBox.Results.Archive import Archive
except ImportError:
    Archive = object


class ArchiveZip(Archive if Archive != object else object):
    """
    ZIP archive format handler.
    
    Handles ZIP file creation and extraction.
    """

    def __init__(self, **params):
        """Initialize ZIP archive handler."""
        super().__init__(**params)

    def format(self) -> str:
        """Get archive format."""
        return 'zip'

    def order(self) -> int:
        """Get processing order."""
        return 10

