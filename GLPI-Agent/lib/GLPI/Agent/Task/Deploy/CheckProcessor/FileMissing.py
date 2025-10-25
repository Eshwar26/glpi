"""
GLPI Agent Task Deploy CheckProcessor FileMissing Module
"""

import os


class FileMissing:
    """Check if a file is missing"""
    
    def __init__(self, path, logger=None):
        """Initialize file missing check"""
        self.path = path
        self.logger = logger
        self._on_success = None
        self._on_failure = None
    
    def prepare(self) -> None:
        """Prepare check messages"""
        self._on_failure = f"{self.path} file exists"
        self._on_success = f"{self.path} file is missing"
    
    def success(self) -> bool:
        """Check if file is missing"""
        return not os.path.isfile(self.path)
    
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
