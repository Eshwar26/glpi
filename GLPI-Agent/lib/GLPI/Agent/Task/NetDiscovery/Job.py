"""
GLPI Agent Task NetDiscovery Job Module

Handles network discovery job configuration and queue management.
"""

from typing import List, Dict, Optional, Tuple, Any
import ipaddress


class NetDiscoveryJob:
    """NetDiscovery Job Handler"""
    
    def __init__(self, logger=None, params=None, credentials=None, ranges=None,
                 file=None, netscan=False, showcontrol=False, localtask=False):
        """
        Initialize a NetDiscovery job.
        
        Args:
            logger: Logger instance
            params: Job parameters
            credentials: SNMP/Remote credentials
            ranges: IP ranges to scan
            file: SNMP walk file path
            netscan: Whether this is a netscan job
            showcontrol: Whether to show control information
            localtask: Whether this is a local task
        """
        self.logger = logger
        self._params = params or {}
        self._credentials = credentials or []
        self._ranges = ranges or []
        self._snmpwalk = file
        self._netscan = netscan
        self._control = showcontrol
        self._localtask = localtask
        self._queue = None
    
    def pid(self) -> int:
        """Get process ID"""
        return self._params.get('PID', 0)
    
    def timeout(self) -> int:
        """Get timeout value"""
        return self._params.get('TIMEOUT', 60)
    
    def max_threads(self) -> int:
        """Get maximum number of threads"""
        return self._params.get('THREADS_DISCOVERY', 1)
    
    def netscan(self) -> bool:
        """Check if this is a netscan job"""
        return self._netscan
    
    def control(self) -> bool:
        """Check if control should be shown"""
        return self._control
    
    def localtask(self) -> bool:
        """Check if this is a local task"""
        return self._localtask
    
    def get_queue_params(self, range_config: Dict) -> Tuple[bool, Optional[Dict]]:
        """
        Get queue parameters for an IP range.
        
        Args:
            range_config: Range configuration dictionary
        
        Returns:
            Tuple of (success, params)
        """
        start = range_config.get('start')
        end = range_config.get('end')
        
        if not start or not end:
            return False, None
        
        try:
            # Create IP network from range
            start_ip = ipaddress.ip_address(start)
            end_ip = ipaddress.ip_address(end)
            
            # Calculate size
            size = int(end_ip) - int(start_ip) + 1
            
            if size <= 0:
                if self.logger:
                    self.logger.error(f"Skipping empty range: {start}-{end}")
                return False, None
            
            if self.logger:
                self.logger.debug(f"initializing block {start}-{end}")
            
            # Store the current IP for iteration
            range_config['current_ip'] = start_ip
            range_config['end_ip'] = end_ip
            range_config['block'] = (start_ip, end_ip)
            
            params = {
                'size': size,
                'range': range_config
            }
            
            return True, params
            
        except (ValueError, ipaddress.AddressValueError) as e:
            if self.logger:
                self.logger.error(f"IPv4 range not supported: {start}-{end}: {e}")
            return False, None
    
    def update_queue(self, size: int = 0, range_config: Optional[Dict] = None) -> None:
        """
        Update the queue with new size and range.
        
        Args:
            size: Size to add to queue
            range_config: Range configuration to add
        """
        if not self._queue:
            return
        
        self._queue['size'] += size
        
        if range_config:
            self._queue['ranges'].append(range_config)
    
    def queuesize(self) -> int:
        """Get the current queue size"""
        if not self._queue:
            return 0
        
        return self._queue.get('size', 0)
    
    def started(self) -> bool:
        """Check if the queue has been started"""
        if not self._queue:
            return False
        
        if self._queue.get('started'):
            return True
        
        # Mark as started for next time
        self._queue['started'] = True
        return False
    
    def done(self) -> bool:
        """
        Mark one item as done and check if all items are done.
        
        Returns:
            True if all items are done, False otherwise
        """
        if not self._queue:
            return False
        
        self._queue['in_queue'] -= 1
        self._queue['done'] += 1
        
        return self._queue['done'] >= self._queue['size']
    
    def max_in_queue(self) -> bool:
        """Check if the queue has reached maximum capacity"""
        if not self._queue:
            return False
        
        return self._queue['in_queue'] >= self.max_threads()
    
    def range(self) -> Optional[Dict]:
        """Get the current range"""
        if not self._queue or not self._queue['ranges']:
            return None
        
        return self._queue['ranges'][0]
    
    def nextip(self) -> Optional[str]:
        """
        Get the next IP address from the queue.
        
        Returns:
            Next IP address as string, or None if queue is empty
        """
        if not self._queue or not self._queue['ranges']:
            return None
        
        range_config = self._queue['ranges'][0]
        
        if 'current_ip' not in range_config or 'end_ip' not in range_config:
            return None
        
        current_ip = range_config['current_ip']
        end_ip = range_config['end_ip']
        
        # Get current IP as string
        blockip = str(current_ip)
        
        # Increment for next iteration
        if current_ip < end_ip:
            range_config['current_ip'] = current_ip + 1
        else:
            # Range is exhausted, remove it
            self._queue['ranges'].pop(0)
        
        if blockip:
            self._queue['in_queue'] += 1
        
        return blockip
    
    def ranges(self) -> List[Dict]:
        """
        Get all ranges for the job.
        
        Returns:
            List of range configurations
        """
        # After _queue has been defined, return the queue ranges count
        if self._queue:
            return self._queue['ranges']
        
        snmp_credentials, remote_credentials = self._get_valid_credentials()
        
        self._queue = {
            'in_queue': 0,
            'snmp_credentials': snmp_credentials or [],
            'remote_credentials': remote_credentials or [],
            'ranges': [],
            'size': 0,
            'done': 0,
            'started': False
        }
        
        ranges = []
        
        for range_config in self._ranges:
            thisrange = {
                'name': range_config.get('NAME', ''),
                'ports': self._get_snmp_ports(range_config.get('PORT')),
                'domains': self._get_snmp_protocols(range_config.get('PROTOCOL')),
                'entity': range_config.get('ENTITY'),
                'start': range_config.get('IPSTART'),
                'end': range_config.get('IPEND'),
                'walk': self._snmpwalk
            }
            
            # Support ToolBox model where credentials are linked to range
            if range_config.get('NAME'):
                snmp_creds, remote_creds = self._get_valid_credentials(range_config['NAME'])
                thisrange['snmp_credentials'] = snmp_creds or []
                thisrange['remote_credentials'] = remote_creds or []
            
            ranges.append(thisrange)
        
        return ranges
    
    def snmp_credentials(self) -> Optional[List[Dict]]:
        """Get SNMP credentials"""
        if not self._queue:
            return None
        
        return self._queue['snmp_credentials']
    
    def remote_credentials(self) -> Optional[List[Dict]]:
        """Get remote credentials"""
        if not self._queue:
            return None
        
        return self._queue['remote_credentials']
    
    def _get_valid_credentials(self, name: Optional[str] = None) -> Tuple[List[Dict], List[Dict]]:
        """
        Get valid credentials for the job.
        
        Args:
            name: Optional range name for ToolBox model
        
        Returns:
            Tuple of (snmp_credentials, remote_credentials)
        """
        snmp_credentials = []
        remote_credentials = []
        
        # Support ToolBox model where credentials are linked to range
        if name and not isinstance(self._credentials, dict):
            return snmp_credentials, remote_credentials
        
        if not name and isinstance(self._credentials, dict):
            return snmp_credentials, remote_credentials
        
        credentials = self._credentials.get(name) if name else self._credentials
        
        if not credentials:
            return snmp_credentials, remote_credentials
        
        snmp_count = 0
        valid_snmp = 0
        invalid_snmp = 0
        remote_count = 0
        valid_remote = 0
        invalid_remote = 0
        
        for credential in credentials:
            cred_type = credential.get('TYPE', 'snmp')
            
            # Skip invalid types
            if cred_type and cred_type not in ['snmp', 'esx', 'ssh', 'winrm']:
                continue
            
            # Handle SNMP credentials
            if cred_type in [None, 'snmp']:
                snmp_count += 1
                
                if credential.get('VERSION') == '3':
                    # Username required for SNMPv3
                    if not credential.get('USERNAME'):
                        if not invalid_snmp and self.logger:
                            self.logger.warning("No username defined for a SNMPv3 credential")
                        invalid_snmp += 1
                        continue
                    
                    # DES support required (would check for Crypt::DES module in Perl)
                    # In Python, we could check for pysnmp or similar
                    # For now, we'll assume it's available
                    
                elif not credential.get('COMMUNITY'):
                    if not invalid_snmp and self.logger:
                        self.logger.warning("No community defined for a credential")
                    invalid_snmp += 1
                    continue
                
                valid_snmp += 1
                snmp_credentials.append(credential)
            
            # Handle remote credentials
            else:
                remote_count += 1
                
                if not credential.get('USERNAME'):
                    if not invalid_remote and self.logger:
                        self.logger.warning(f"No username defined for a {cred_type} credential")
                    invalid_remote += 1
                    continue
                
                if cred_type in ['esx', 'winrm']:
                    password = credential.get('PASSWORD', '')
                    if not password:
                        if not invalid_remote and self.logger:
                            self.logger.warning(f"No password defined for a {cred_type} credential")
                        invalid_remote += 1
                        continue
                
                if cred_type in ['ssh', 'winrm']:
                    port = credential.get('PORT')
                    if port is not None:
                        try:
                            port = int(port)
                            if port < 0 or port > 65535:
                                raise ValueError()
                        except (ValueError, TypeError):
                            if not invalid_remote and self.logger:
                                self.logger.warning(f"Not valid port defined for a {cred_type} credential")
                            invalid_remote += 1
                            continue
                
                valid_remote += 1
                remote_credentials.append(credential)
        
        if snmp_count and not valid_snmp and self.logger:
            self.logger.warning("No valid SNMP credential defined for this scan")
        
        if remote_count and not valid_remote and self.logger:
            self.logger.warning("No valid remote credential defined for this scan")
        
        return snmp_credentials, remote_credentials
    
    @staticmethod
    def _get_snmp_ports(ports: Any) -> List[int]:
        """
        Parse and validate SNMP ports.
        
        Args:
            ports: Port specification (string, list, or comma-separated)
        
        Returns:
            List of valid port numbers
        """
        if not ports:
            return []
        
        # Convert to list of strings
        if isinstance(ports, str):
            given_ports = [ports]
        elif isinstance(ports, list):
            given_ports = ports
        else:
            given_ports = [str(ports)]
        
        # Split comma-separated values
        all_ports = []
        for port in given_ports:
            all_ports.extend([p.strip() for p in str(port).split(',')])
        
        # Validate and deduplicate
        valid_ports = set()
        for port in all_ports:
            try:
                port_num = int(port)
                if 0 < port_num < 65536:
                    valid_ports.add(port_num)
            except (ValueError, TypeError):
                continue
        
        return sorted(list(valid_ports))
    
    @staticmethod
    def _get_snmp_protocols(protocols: Any) -> List[str]:
        """
        Parse and validate SNMP protocols.
        
        Args:
            protocols: Protocol specification (string, list, or comma-separated)
        
        Returns:
            List of valid protocol names
        """
        if not protocols:
            return []
        
        # Supported protocols
        supported_protocols = [
            'udp',
            'udp/ipv4',
            'udp/ipv6',
            'tcp',
            'tcp/ipv4',
            'tcp/ipv6'
        ]
        
        # Convert to list of strings
        if isinstance(protocols, str):
            given_protocols = [protocols]
        elif isinstance(protocols, list):
            given_protocols = protocols
        else:
            given_protocols = [str(protocols)]
        
        # Split comma-separated values
        all_protocols = []
        for proto in given_protocols:
            all_protocols.extend([p.strip() for p in str(proto).split(',')])
        
        # Filter and order by supported protocols
        protocol_set = {p.lower() for p in all_protocols if p}
        result = []
        
        for proto in supported_protocols:
            if proto in protocol_set:
                result.append(proto)
        
        return result
