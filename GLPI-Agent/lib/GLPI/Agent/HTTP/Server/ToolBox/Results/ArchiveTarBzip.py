"""
GLPI Agent ToolBox Results ArchiveTarBzip Module

TAR.BZ2 archive format handler.
"""

try:
    from GLPI.Agent.HTTP.Server.ToolBox.Results.Archive import Archive
except ImportError:
    Archive = object


class ArchiveTarBzip(Archive if Archive != object else object):
    """
    TAR.BZ2 archive format handler.
    
    Handles TAR.BZ2 (bzip2 compressed tar) file creation and extraction.
    """

    def __init__(self, **params):
        """Initialize TAR.BZ2 archive handler."""
        super().__init__(**params)

    def format(self) -> str:
        """Get archive format."""
        return 'tar.bz2'

    def order(self) -> int:
        """Get processing order."""
        return 21

