"""
GLPI Agent ToolBox Results ArchiveTarGzip Module

TAR.GZ archive format handler.
"""

try:
    from GLPI.Agent.HTTP.Server.ToolBox.Results.Archive import Archive
except ImportError:
    Archive = object


class ArchiveTarGzip(Archive if Archive != object else object):
    """
    TAR.GZ archive format handler.
    
    Handles TAR.GZ (gzipped tar) file creation and extraction.
    """

    def __init__(self, **params):
        """Initialize TAR.GZ archive handler."""
        super().__init__(**params)

    def format(self) -> str:
        """Get archive format."""
        return 'tar.gz'

    def order(self) -> int:
        """Get processing order."""
        return 20

