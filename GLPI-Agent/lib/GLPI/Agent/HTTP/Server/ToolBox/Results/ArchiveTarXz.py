"""
GLPI Agent ToolBox Results ArchiveTarXz Module

TAR.XZ archive format handler.
"""

try:
    from GLPI.Agent.HTTP.Server.ToolBox.Results.Archive import Archive
except ImportError:
    Archive = object


class ArchiveTarXz(Archive if Archive != object else object):
    """
    TAR.XZ archive format handler.
    
    Handles TAR.XZ (xz compressed tar) file creation and extraction.
    """

    def __init__(self, **params):
        """Initialize TAR.XZ archive handler."""
        super().__init__(**params)

    def format(self) -> str:
        """Get archive format."""
        return 'tar.xz'

    def order(self) -> int:
        """Get processing order."""
        return 22

