"""
GLPI Agent Task NetInventory Job Module

Handles network inventory job configuration and queue management.
"""

from typing import List, Dict, Optional, Any


class NetInventoryJob:
    """NetInventory Job Handler"""
    
    def __init__(self, logger=None, params=None, credentials=None, devices=None, showcontrol=False):
        """
        Initialize a NetInventory job.
        
        Args:
            logger: Logger instance
            params: Job parameters
            credentials: SNMP credentials
            devices: List of devices to inventory
            showcontrol: Whether to show control information
        """
        self.logger = logger
        self._params = params or {}
        self._credentials = credentials or []
        self._devices = devices if isinstance(devices, list) else []
        self._count = len(self._devices)
        self._control = showcontrol
        self._queue = None
    
    def pid(self) -> int:
        """Get process ID"""
        return self._params.get('PID', 0)
    
    def timeout(self) -> int:
        """Get timeout value"""
        return self._params.get('TIMEOUT', 60)
    
    def max_threads(self) -> int:
        """Get maximum number of threads"""
        return self._params.get('THREADS_QUERY', 1)
    
    def count(self) -> int:
        """Get device count"""
        return self._count
    
    def devices(self) -> List[Dict]:
        """Get all devices"""
        return self._devices.copy()
    
    def skip_start_stop(self) -> bool:
        """Check if start/stop messages should be skipped"""
        return self._params.get('NO_START_STOP', False)
    
    def credential(self, cred_id: str) -> Optional[Dict]:
        """
        Get a credential by ID.
        
        Args:
            cred_id: Credential ID
        
        Returns:
            Credential dictionary or None
        """
        if not self._credentials:
            if self.logger:
                self.logger.warning("No SNMP credential defined for this job")
            return None
        
        if not self._credentials:
            if self.logger:
                self.logger.warning("No SNMP credential provided for this job")
            return None
        
        # Find credential by ID
        for credential in self._credentials:
            if credential.get('ID') == cred_id:
                return credential
        
        if self.logger:
            self.logger.warning(f"No SNMP credential with {cred_id} ID provided")
        
        return None
    
    def update_queue(self, devices: List[Dict]) -> None:
        """
        Update the queue with new devices.
        
        Args:
            devices: List of devices to add
        """
        if not devices:
            return
        
        if not self._queue:
            self._queue = {
                'in_queue': 0,
                'todo': []
            }
        
        self._queue['todo'].extend(devices)
    
    def done(self) -> bool:
        """
        Mark one device as done and check if all devices are done.
        
        Returns:
            True if all devices are done, False otherwise
        """
        if not self._queue:
            return False
        
        self._queue['in_queue'] -= 1
        
        return self._queue['in_queue'] == 0 and len(self._queue['todo']) == 0
    
    def no_more(self) -> bool:
        """
        Check if there are no more devices in the queue.
        
        Returns:
            True if no more devices, False otherwise
        """
        if not self._queue:
            return False
        
        return len(self._queue['todo']) == 0
    
    def max_in_queue(self) -> bool:
        """Check if the queue has reached maximum capacity"""
        if not self._queue:
            return False
        
        return self._queue['in_queue'] >= self.max_threads()
    
    def nextdevice(self) -> Optional[Dict]:
        """
        Get the next device from the queue.
        
        Returns:
            Next device dictionary, or None if queue is empty
        """
        if not self._queue or not self._queue['todo']:
            return None
        
        device = self._queue['todo'].pop(0)
        self._queue['in_queue'] += 1
        
        return device
    
    def control(self) -> bool:
        """Check if control should be shown"""
        return self._control
