"""
GLPI Agent HTTP Session Module

This module provides HTTP session management for the GLPI Agent.
It handles session state, nonce generation, and authorization.
"""

import time
import random
import hashlib
import base64
from typing import Optional, Dict, Any, List, Tuple

from GLPI.Agent.Logger import Logger


# Log prefix for session messages
LOG_PREFIX = "[http session] "


class Session:
    """
    HTTP Session class for managing peer connection status.
    
    Provides session ID generation, nonce-based authorization,
    expiration tracking, and data storage.
    """

    def __init__(self, **params):
        """
        Initialize an HTTP session.
        
        Args:
            **params: Session parameters including:
                - logger: Logger instance (default: new Logger)
                - timer: Initial timer as [start_time, timeout] (default: [now, 600])
                - timeout: Session timeout in seconds (default: 600)
                - nonce: Pre-existing nonce for session restoration
                - sid: Pre-existing session ID for restoration
                - infos: Session info string
                - _*: Any parameter starting with _ is stored as data
        """
        self.logger = params.get('logger') or Logger()
        
        timeout = params.get('timeout', 600)
        self.timer = params.get('timer', [time.time(), timeout])
        
        self.nonce_value = params.get('nonce', '')
        self._sid = params.get('sid', '')
        self._info = params.get('infos', '')
        
        # Data storage
        self.datas: Dict[str, Any] = {}
        self._keep: Dict[str, Any] = {}
        
        # Generate a random session ID if not provided
        if not self._sid:
            self._sid = self._generate_sid()
        
        # Include private params (those starting with _) as data
        for key, value in params.items():
            if key.startswith('_') and len(key) > 1:
                data_key = key[1:]  # Remove leading underscore
                self.datas[data_key] = value

    def _generate_sid(self) -> str:
        """
        Generate a random session ID.
        
        Returns:
            A random session ID in format XXXX-XXXX-XXXX-XXXX
        """
        parts = []
        for _ in range(4):
            # Generate random 16-bit value and format as hex
            rand_val = random.randint(0, 65535)
            hex_str = format(rand_val, '04x')
            parts.append(hex_str)
        return '-'.join(parts)

    def info(self, *args) -> str:
        """
        Set or get session information.
        
        If arguments are provided, they are joined and stored as info.
        
        Args:
            *args: Optional info strings to store
            
        Returns:
            Complete info string including SID and expiration
        """
        if args:
            self._info = ' ; '.join(str(arg) for arg in args)
        
        infos = [self._sid]
        if self._info:
            infos.append(self._info)
        
        # Add expiration time
        expiration_time = self.timer[0] + self.timer[1]
        expiration_str = time.strftime(
            '%a %b %d %H:%M:%S %Y',
            time.localtime(expiration_time)
        )
        infos.append(f"expiration on {expiration_str}")
        
        return ' ; '.join(infos)

    def sid(self) -> str:
        """
        Get the session ID.
        
        Returns:
            The session ID string
        """
        return self._sid or ''

    def expired(self) -> bool:
        """
        Check if the session has expired.
        
        Returns:
            True if session has expired, False otherwise
        """
        if isinstance(self.timer, list) and len(self.timer) >= 2:
            return self.timer[0] + self.timer[1] < time.time()
        return False

    def nonce(self) -> str:
        """
        Get or generate a nonce for the session.
        
        Returns:
            The session nonce (base64 encoded)
        """
        if not self.nonce_value:
            try:
                # Create SHA-1 hash
                sha = hashlib.sha1()
                
                # Add 32 random bytes
                for _ in range(32):
                    sha.update(bytes([random.randint(0, 255)]))
                
                # Get base64 digest
                self.nonce_value = base64.b64encode(sha.digest()).decode('ascii')
                
            except Exception as e:
                self.logger.debug(f"{LOG_PREFIX}Nonce failure: {e}")
        
        return self.nonce_value

    def authorized(self, **params) -> bool:
        """
        Check if a request is authorized based on token and payload.
        
        Args:
            **params: Parameters including:
                - token: Authorization token
                - payload: Expected payload digest
                
        Returns:
            True if authorized, False otherwise
        """
        token = params.get('token')
        payload = params.get('payload')
        
        if not token or not payload:
            return False
        
        try:
            # Create SHA-256 hash
            sha = hashlib.sha256()
            
            # Compute digest: SHA256(nonce ++ '++' ++ token)
            auth_string = f"{self.nonce_value}++{token}"
            sha.update(auth_string.encode('utf-8'))
            
            # Get base64 digest
            digest = base64.b64encode(sha.digest()).decode('ascii')
            
            return digest == payload
            
        except Exception as e:
            self.logger.debug(f"{LOG_PREFIX}Digest failure: {e}")
            return False

    def dump(self) -> Dict[str, Any]:
        """
        Dump session state for persistence.
        
        Returns:
            Dictionary containing session state
        """
        dump = {}
        
        if self.nonce_value:
            dump['nonce'] = self.nonce_value
        
        if self.timer:
            dump['timer'] = self.timer
        
        if self._info:
            dump['infos'] = self._info
        
        # Include data with underscore prefix
        if self.datas:
            for key, value in self.datas.items():
                dump[f'_{key}'] = value
        
        return dump

    def set(self, data: str, value: Any = None):
        """
        Store data in the session.
        
        Updates the session timer.
        
        Args:
            data: Data key
            value: Value to store (default: empty string)
        """
        # Update session time
        self.timer[0] = time.time()
        
        if not data:
            return
        
        self.datas[data] = value if value is not None else ""

    def get(self, data: str) -> Optional[Any]:
        """
        Retrieve data from the session.
        
        Updates the session timer.
        
        Args:
            data: Data key to retrieve
            
        Returns:
            The stored value or None
        """
        # Update session time
        self.timer[0] = time.time()
        
        if not data or not self.datas:
            return None
        
        return self.datas.get(data)

    def delete(self, data: str):
        """
        Delete data from the session.
        
        Updates the session timer.
        
        Args:
            data: Data key to delete
        """
        # Update session time
        self.timer[0] = time.time()
        
        if not data or not self.datas:
            return
        
        self.datas.pop(data, None)

    def keep(self, data: str, value: Any = None):
        """
        Keep data in memory (not exported by dump).
        
        Args:
            data: Data key
            value: Value to keep (default: empty string)
        """
        if not data:
            return
        
        self._keep[data] = value if value is not None else ""

    def kept(self, data: str) -> Optional[Any]:
        """
        Retrieve data kept in memory.
        
        Args:
            data: Data key to retrieve
            
        Returns:
            The kept value or None
        """
        if not data or not self._keep:
            return None
        
        return self._keep.get(data)

    def forget(self, data: str):
        """
        Forget data kept in memory.
        
        Args:
            data: Data key to forget
        """
        if not data or not self._keep:
            return
        
        self._keep.pop(data, None)

