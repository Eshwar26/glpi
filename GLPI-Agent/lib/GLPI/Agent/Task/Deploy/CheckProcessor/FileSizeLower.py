"""
GLPI Agent Task Deploy CheckProcessor FileSizeLower Module
"""

import os


class FileSizeLower:
    """Check if file size is lower than expected value"""
    
    def __init__(self, path, value=None, logger=None):
        """Initialize file size lower check"""
        self.path = path
        self.value = value
        self.logger = logger
        self._on_success = None
        self._on_failure = None
    
    def prepare(self) -> None:
        """Prepare check messages"""
        pass
    
    def success(self) -> bool:
        """Check if file size is lower than expected"""
        self._on_failure = f"{self.path} is missing"
        if not os.path.isfile(self.path):
            return False
        
        self._on_failure = "no value provided to check file size against"
        upper = self.value
        if upper is None:
            return False
        
        try:
            size = os.path.getsize(self.path)
        except Exception as e:
            self._on_failure = f"{self.path} file stat failure, {e}"
            return False
        
        self._on_failure = f"{self.path} file size not lower: {size} >= {upper}"
        self._on_success = f"{self.path} file size is lower: {size} < {upper}"
        return size < upper
    
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
