"""
GLPI Agent Task Deploy CheckProcessor FileSizeEquals Module
"""

import os


class FileSizeEquals:
    """Check if file size equals expected value"""
    
    def __init__(self, path, value=None, logger=None):
        """Initialize file size equals check"""
        self.path = path
        self.value = value
        self.logger = logger
        self._on_success = None
        self._on_failure = None
    
    def prepare(self) -> None:
        """Prepare check messages"""
        self._on_success = f"{self.path} expected file size: {self.value or 'n/a'}"
    
    def success(self) -> bool:
        """Check if file size equals expected"""
        self._on_failure = f"{self.path} is missing"
        if not os.path.isfile(self.path):
            return False
        
        self._on_failure = "no value provided to check file size against"
        expected = self.value
        if expected is None:
            return False
        
        try:
            size = os.path.getsize(self.path)
        except Exception as e:
            self._on_failure = f"{self.path} file stat failure, {e}"
            return False
        
        self._on_failure = f"{self.path} has wrong file size: {size} vs {expected}"
        return size == expected
    
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
