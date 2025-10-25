"""
GLPI Agent Task Deploy CheckProcessor DirectoryMissing Module
"""

import os


class DirectoryMissing:
    """Check if a directory is missing"""
    
    def __init__(self, path, logger=None):
        """Initialize directory missing check"""
        self.path = path
        self.logger = logger
        self._on_success = None
        self._on_failure = None
    
    def prepare(self) -> None:
        """Prepare check messages"""
        self._on_failure = f"{self.path} directory exists"
        self._on_success = f"{self.path} directory is missing"
    
    def success(self) -> bool:
        """Check if directory is missing"""
        return not os.path.isdir(self.path)
    
    def on_failure(self, msg: str = None) -> str:
        """Get or set failure message"""
        if msg:
            self._on_failure = msg
        return self._on_failure or ""
    
    def on_success(self, msg: str = None) -> str:
        """Get or set success message"""
        if msg:
            self._on_success = msg
        return self._on_success or ""
