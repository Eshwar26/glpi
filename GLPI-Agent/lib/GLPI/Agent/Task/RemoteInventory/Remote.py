"""
GLPI Agent Task RemoteInventory Remote Module

Base class for remote inventory connections.
"""

from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, parse_qs, unquote


class Remote:
    """Base class for remote inventory connections"""
    
    # Override in subclasses
    supported = False
    supported_modes = ()
    
    def __init__(self, logger=None, config=None, url=None, dump=None, timeout=0):
        """
        Initialize a remote connection.
        
        Args:
            logger: Logger instance
            config: Configuration dictionary
            url: Remote URL
            dump: Stored remote data
            timeout: Connection timeout
        """
        import os
        
        dump = dump or {}
        
        self._expiration = dump.get('expiration', 0)
        self._deviceid = dump.get('deviceid', '')
        self._url = dump.get('url', url)
        self._config = config or {}
        self._user = os.environ.get('USERNAME')
        self._pass = os.environ.get('PASSWORD')
        self._modes = {}
        self._timeout = timeout
        self.logger = logger
        self._protocol = None
        self._host = None
        self._port = None
        
        if not self._url:
            return
        
        # Parse URL
        parsed_url = urlparse(self._url)
        scheme = parsed_url.scheme
        
        if not scheme:
            # Default to SSH
            scheme = 'ssh'
            self._url = f"{scheme}://{self._url}"
            parsed_url = urlparse(self._url)
        
        self._protocol = scheme
        
        # Parse query parameters for mode and deviceid
        query_params = parse_qs(parsed_url.query)
        
        if 'mode' in query_params:
            mode = query_params['mode'][0]
            for key in mode.lower().split('_'):
                if key in self.supported_modes:
                    self._modes[key] = True
                elif self.logger:
                    self.logger.debug(f"Unsupported remote mode: {key}")
            
            if self._modes and self.logger:
                self.logger.debug(f"Remote mode enabled: {' '.join(self._modes.keys())}")
        
        if 'deviceid' in query_params and not self._deviceid:
            self._deviceid = query_params['deviceid'][0]
        
        self.handle_url(parsed_url)
    
    def handle_url(self, parsed_url) -> None:
        """
        Handle URL parsing and extract credentials.
        
        Args:
            parsed_url: Parsed URL object
        """
        self._host = parsed_url.hostname
        self._port = parsed_url.port
        
        if parsed_url.username:
            self.user(unquote(parsed_url.username))
        
        if parsed_url.password:
            self.pass_(unquote(parsed_url.password))
    
    def url(self) -> str:
        """Get the remote URL"""
        return self._url
    
    def safe_url(self) -> Optional[str]:
        """Get a safe URL (without credentials) for identification"""
        if not self._url:
            return None
        
        parsed = urlparse(self._url)
        # Remove password from URL
        safe_netloc = parsed.hostname
        if parsed.port:
            safe_netloc += f":{parsed.port}"
        
        safe_url = f"{parsed.scheme}://{safe_netloc}{parsed.path}"
        if parsed.query:
            safe_url += f"?{parsed.query}"
        
        return safe_url
    
    def deviceid(self, deviceid: Optional[str] = None) -> Optional[str]:
        """Get or set device ID"""
        if deviceid is not None:
            self._deviceid = deviceid
        return self._deviceid
    
    def user(self, user: Optional[str] = None) -> Optional[str]:
        """Get or set username"""
        if user is not None:
            self._user = user
        return self._user
    
    def pass_(self, password: Optional[str] = None) -> Optional[str]:
        """Get or set password"""
        if password is not None:
            self._pass = password
        return self._pass
    
    def mode(self, mode: str) -> bool:
        """Check if a mode is enabled"""
        return mode in self._modes
    
    def expiration(self, expiration: Optional[int] = None) -> int:
        """Get or set expiration time"""
        if expiration is not None:
            self._expiration = expiration
        return self._expiration
    
    def has_expired(self) -> bool:
        """Check if the remote has expired"""
        import time
        return self._expiration > 0 and time.time() > self._expiration
    
    def dump(self) -> Dict[str, Any]:
        """Dump remote data for storage"""
        return {
            'url': self._url,
            'deviceid': self._deviceid,
            'expiration': self._expiration
        }
    
    def checking_error(self, error: str) -> None:
        """Log a checking error"""
        if self.logger:
            self.logger.error(f"Remote inventory checking failure on {self._url}: {error}")
    
    def run_error(self, error: str) -> None:
        """Log a run error"""
        if self.logger:
            self.logger.error(f"Remote inventory failure on {self._url}: {error}")
