"""
GLPI Agent Task RemoteInventory Module

This module performs inventory of remote systems via SSH or WinRM.
"""

from typing import List, Dict, Optional, Any

from GLPI.Agent.Task.RemoteInventory.Version import VERSION
from GLPI.Agent.Task.RemoteInventory.Remotes import Remotes

__version__ = VERSION


class RemoteInventoryTask:
    """GLPI Agent Remote Inventory Task"""
    
    def __init__(self, logger=None, config=None, target=None, deviceid=None, storage=None):
        """Initialize the RemoteInventory task"""
        self.logger = logger
        self.config = config
        self.target = target
        self.deviceid = deviceid
        self.storage = storage
        self.remotes = None
    
    def is_enabled(self) -> bool:
        """Check if the task is enabled"""
        # RemoteInventory can work with any target type
        return True
    
    def run(self) -> Optional[bool]:
        """Run the remote inventory task"""
        # Just reset event if run as an event to not trigger another one
        if hasattr(self, 'reset_event'):
            self.reset_event()
        
        if not self.storage:
            if self.logger:
                self.logger.error("No storage available for RemoteInventory task")
            return False
        
        # Initialize remotes manager
        try:
            self.remotes = Remotes(
                logger=self.logger,
                config=self.config,
                storage=self.storage
            )
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to initialize remotes: {e}")
            return False
        
        # Clean expired remotes
        if self.remotes:
            expired_count = self.remotes.clean_expired()
            if expired_count > 0 and self.logger:
                self.logger.info(f"Cleaned {expired_count} expired remote(s)")
        
        # Get all remotes to inventory
        if not self.remotes or self.remotes.count() == 0:
            if self.logger:
                self.logger.info("No remotes configured for inventory")
            return True
        
        if self.logger:
            self.logger.info(f"Processing {self.remotes.count()} remote(s)")
        
        # Process each remote
        for remote in self.remotes.getall():
            self.process_remote(remote)
        
        # Save remotes state
        if self.remotes:
            self.remotes.save()
        
        return True
    
    def process_remote(self, remote) -> bool:
        """
        Process a single remote inventory.
        
        Args:
            remote: Remote instance
        
        Returns:
            True if successful, False otherwise
        """
        # This is a placeholder for the actual implementation
        # The real implementation would:
        # 1. Connect to the remote system
        # 2. Run inventory command
        # 3. Parse the inventory data
        # 4. Send to server or save locally
        
        if self.logger:
            self.logger.debug(f"Processing remote: {remote.url()}")
        
        return True
