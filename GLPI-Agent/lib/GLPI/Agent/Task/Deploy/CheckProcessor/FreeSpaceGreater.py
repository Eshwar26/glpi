"""
GLPI Agent Task Deploy CheckProcessor FreeSpaceGreater Module
"""

import shutil


class FreeSpaceGreater:
    """Check if free space is greater than expected value"""
    
    def __init__(self, path, value=None, logger=None):
        """Initialize free space greater check"""
        self.path = path
        self.value = value
        self.logger = logger
        self._on_success = None
        self._on_failure = None
    
    def prepare(self) -> None:
        """Prepare check messages"""
        pass
    
    def success(self) -> bool:
        """Check if free space is greater than expected"""
        self._on_failure = "no value provided to check free space against"
        lower = self.value
        if lower is None:
            return False
        
        try:
            stat = shutil.disk_usage(self.path)
            freespace = stat.free
        except Exception as e:
            self._on_failure = f"{self.path} free space not found, {e}"
            return False
        
        self._on_failure = f"{self.path} free space not greater: {freespace} <= {lower}"
        self._on_success = f"{self.path} free space is greater: {freespace} > {lower}"
        return freespace > lower
    
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
