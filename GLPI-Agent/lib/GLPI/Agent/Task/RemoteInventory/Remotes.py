"""
GLPI Agent Task RemoteInventory Remotes Module

Manages multiple remote inventory connections.
"""

from typing import Dict, List, Optional, Any

from GLPI.Agent.Task.RemoteInventory.Remote import Remote


class Remotes:
    """Manager for remote inventory connections"""
    
    def __init__(self, logger=None, config=None, storage=None):
        """
        Initialize remotes manager.
        
        Args:
            logger: Logger instance
            config: Configuration dictionary
            storage: Storage instance for persisting remotes
        """
        if not storage:
            raise ValueError('no storage parameter')
        
        self._config = config or {}
        self._count = 0
        self._remotes = {}
        self.logger = logger
        self._storage = None
        
        # Handle remotes from --remote option or load them from storage
        if self._config.get('remote'):
            for url in self._config['remote'].split(','):
                url = url.strip()
                if not url:
                    continue
                
                # Skip if URL is already known
                if any(remote.url() == url for remote in self.getall()):
                    continue
                
                remote = Remote(
                    url=url,
                    config=self._config,
                    logger=logger
                )
                
                if not remote.supported:
                    continue
                
                remote_id = remote.safe_url()
                if not remote_id:
                    continue
                
                # Don't overwrite if already known
                if remote_id in self._remotes:
                    continue
                
                self._remotes[remote_id] = remote
                self._count += 1
        else:
            # Keep storage for expiration management
            self._storage = storage
            
            # Load remotes from storage
            remotes = storage.restore(name='remotes') or {}
            for remote_id, dump in remotes.items():
                if not isinstance(dump, dict):
                    continue
                
                remote = Remote(
                    dump=dump,
                    config=self._config,
                    logger=self.logger
                )
                
                if not remote.supported:
                    continue
                
                self._remotes[remote_id] = remote
                self._count += 1
    
    def count(self) -> int:
        """Get the number of remotes"""
        return self._count
    
    def get(self, deviceid: str) -> Optional[Remote]:
        """
        Get a remote by device ID.
        
        Args:
            deviceid: Device ID
        
        Returns:
            Remote instance or None
        """
        return self._remotes.get(deviceid)
    
    def getlist(self) -> List[str]:
        """
        Get list of device IDs.
        
        Returns:
            List of device ID strings
        """
        return list(self._remotes.keys())
    
    def getall(self) -> List[Remote]:
        """
        Get all remote instances.
        
        Returns:
            List of Remote instances
        """
        return list(self._remotes.values())
    
    def add(self, remote: Remote) -> bool:
        """
        Add a new remote.
        
        Args:
            remote: Remote instance to add
        
        Returns:
            True if added, False if already exists
        """
        deviceid = remote.deviceid()
        if not deviceid:
            return False
        
        if deviceid in self._remotes:
            return False
        
        self._remotes[deviceid] = remote
        self._count += 1
        
        return True
    
    def del_remote(self, deviceid: str) -> bool:
        """
        Delete a remote by device ID.
        
        Args:
            deviceid: Device ID to delete
        
        Returns:
            True if deleted, False if not found
        """
        if deviceid not in self._remotes:
            return False
        
        del self._remotes[deviceid]
        self._count -= 1
        
        return True
    
    def save(self) -> None:
        """Save remotes to storage"""
        if not self._storage:
            return
        
        # Create dump of all remotes
        remotes_dump = {}
        for deviceid, remote in self._remotes.items():
            remotes_dump[deviceid] = remote.dump()
        
        # Save to storage
        self._storage.save(name='remotes', data=remotes_dump)
    
    def clean_expired(self) -> int:
        """
        Remove expired remotes.
        
        Returns:
            Number of remotes removed
        """
        removed = 0
        expired_ids = []
        
        for deviceid, remote in self._remotes.items():
            if remote.has_expired():
                expired_ids.append(deviceid)
        
        for deviceid in expired_ids:
            if self.del_remote(deviceid):
                removed += 1
                if self.logger:
                    self.logger.debug(f"Removed expired remote: {deviceid}")
        
        return removed
