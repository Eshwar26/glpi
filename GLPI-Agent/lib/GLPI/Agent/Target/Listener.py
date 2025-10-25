# glpi_agent/target/listener.py
"""
Listener Target Implementation for GLPI Agent

HTTP endpoint for receiving inventories from remote agents.
Implements singleton pattern - only one listener per agent instance.
Manages HTTP sessions for remote inventory collection.
"""

import time
import atexit
from typing import List, Optional, Dict, Any

from .base_target import Target
from ..logger import Logger
from ..config import Config
from ..storage import Storage

STORE_SESSION_TIMEOUT = 10

# Only one listener needed by agent instance
_listener = None


class ListenerTarget(Target):
    """
    Listener target for receiving remote inventories via HTTP.
    
    This target acts as an HTTP server endpoint that receives inventory
    data from remote agents. It uses a singleton pattern to ensure only
    one listener exists per agent instance.
    
    Key Features:
    - Singleton pattern for single listener instance
    - Session management for remote agents
    - Persistent session storage
    - Automatic session cleanup and expiration
    - Inventory XML storage
    
    Attributes:
        sessions (Dict[str, Session]): Active HTTP sessions keyed by remote ID
        _inventory (Optional[str]): Stored inventory XML from last submission
        _storing_session_timer (float): Timestamp for next session storage
        _touched_sessions (int): Counter for modified sessions since last save
        _initialized (bool): Flag to prevent re-initialization
    """
    
    def __new__(cls, **params):
        """
        Singleton constructor - returns existing instance if available.
        
        Args:
            **params: Target initialization parameters
            
        Returns:
            The singleton ListenerTarget instance
        """
        global _listener
        
        # Return existing listener if already created
        if _listener is not None:
            return _listener
        
        # Create new instance
        instance = super().__new__(cls)
        _listener = instance
        return instance
    
    def __init__(self, logger: Optional[Logger] = None, 
                 config: Optional[Config] = None, **params):
        """
        Initialize the listener target (only once due to singleton).
        
        Args:
            logger: Logger instance for debugging
            config: Configuration object
            **params: Additional parameters including basevardir
        """
        global _listener
        
        # Only initialize once (singleton pattern)
        if hasattr(self, '_initialized'):
            return
        
        super().__init__(logger=logger, config=config, **params)
        
        # Initialize with special listener storage directory
        self._init(
            id='listener',
            vardir=f"{params.get('basevardir', '/var/lib/glpi-agent')}/__LISTENER__"
        )
        
        # Session management state
        self.sessions: Dict[str, 'Session'] = {}
        self._storing_session_timer: float = time.time() + STORE_SESSION_TIMEOUT
        self._touched_sessions: int = 0
        self._inventory: Optional[str] = None
        
        # Mark as initialized
        self._initialized = True
        
        if self.logger:
            self.logger.debug("Listener target initialized")
    
    @classmethod
    def reset(cls):
        """
        Reset singleton instance.
        
        Primarily used for testing to clear the singleton state.
        """
        global _listener
        if _listener and hasattr(_listener, '_storing_session_timer'):
            # Store sessions before reset
            _listener._storing_session_timer = time.time()
            _listener._store_sessions()
        _listener = None
    
    def getName(self) -> str:
        """
        Return the target name.
        
        Returns:
            'listener' - the fixed name for listener targets
        """
        return 'listener'
    
    def getType(self) -> str:
        """
        Return the target type.
        
        Returns:
            'listener' - identifies this as a listener target
        """
        return 'listener'
    
    def plannedTasks(self, tasks: Optional[List[str]] = None) -> List[str]:
        """
        Get or set planned tasks (always empty for listener).
        
        Listener targets don't initiate tasks - they only receive
        inventories from remote agents via HTTP.
        
        Args:
            tasks: Ignored for listener targets
            
        Returns:
            Empty list - listeners don't plan tasks
        """
        return []
    
    def inventory_xml(self, inventory: Optional[str] = None) -> Optional[str]:
        """
        Set or retrieve inventory XML.
        
        Used to store inventory data received via HTTP and retrieve it
        for processing. Retrieval clears the stored inventory.
        
        Args:
            inventory: XML string to store, or None to retrieve and clear
            
        Returns:
            The stored inventory XML (when retrieving), or the set value
        """
        if inventory is not None:
            # Store new inventory
            self._inventory = inventory
            if self.logger:
                self.logger.debug(
                    f"Stored inventory XML ({len(inventory)} bytes)"
                )
            return inventory
        else:
            # Retrieve and clear inventory
            result = self._inventory
            self._inventory = None
            if result and self.logger:
                self.logger.debug(
                    f"Retrieved inventory XML ({len(result)} bytes)"
                )
            return result
    
    def session(self, **params) -> 'Session':
        """
        Create or retrieve an HTTP session.
        
        Sessions track state for remote inventory collection operations.
        They expire after a timeout period and are persisted to storage.
        
        Args:
            remoteid (str): Remote agent identifier
            timeout (int): Session timeout in seconds
            **params: Additional session parameters
            
        Returns:
            Session object (existing or newly created)
        """
        # Lazy load sessions from storage
        if not self.sessions:
            self.sessions = self._restore_sessions()
        
        remoteid = params.get('remoteid')
        self._touched_sessions += 1
        
        # Try to get existing session
        if remoteid and remoteid in self.sessions:
            session = self.sessions[remoteid]
            if not session.expired():
                if self.logger:
                    self.logger.debug2(f"Reusing existing session: {remoteid}")
                return session
            
            # Session expired - remove it
            if self.logger:
                self.logger.debug(f"Session expired, creating new: {remoteid}")
            del self.sessions[remoteid]
            params.pop('remoteid', None)
        
        # Import Session class here to avoid circular imports
        from ..http.session import Session
        
        # Create new session
        session = Session(
            logger=self.logger,
            timeout=params.get('timeout'),
            sid=params.get('remoteid')
        )
        
        if remoteid:
            self.sessions[remoteid] = session
            if self.logger:
                self.logger.debug(f"Created new session: {remoteid}")
        
        return session
    
    def clean_session(self, session: 'Session'):
        """
        Remove a session from storage.
        
        Called when a session is no longer needed or has completed
        its operation.
        
        Args:
            session: Session object to remove
        """
        if not session:
            return
        
        sid = session.sid()
        if not sid:
            return
        
        # Lazy load sessions
        if not self.sessions:
            self.sessions = self._restore_sessions()
        
        if sid in self.sessions:
            del self.sessions[sid]
            self._touched_sessions += 1
            if self.logger:
                self.logger.debug(f"Cleaned session: {sid}")
    
    def _store_sessions(self):
        """
        Store sessions to persistent storage.
        
        Saves active sessions to disk so they persist across agent restarts.
        Only stores if sessions have been modified and timeout has elapsed.
        """
        # Only store if we have touched sessions and timer has expired
        if not (self._touched_sessions and 
                self._storing_session_timer and 
                time.time() >= self._storing_session_timer):
            return
        
        # Lazy load sessions
        if not self.sessions:
            self.sessions = self._restore_sessions()
        
        # Prepare session data for storage
        datas = {}
        expired_count = 0
        
        for remoteid, session in self.sessions.items():
            if not session.expired():
                datas[remoteid] = session.dump()
            else:
                expired_count += 1
        
        # Save to storage
        try:
            storage = self.getStorage()
            storage.save(name='Sessions', data=datas)
            
            if self.logger:
                self.logger.debug(
                    f"Stored {len(datas)} sessions "
                    f"({expired_count} expired sessions removed)"
                )
            
            # Check for storage errors
            error = storage.error()
            if error and self.logger:
                self.logger.error(f"Session storage error: {error}")
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to store sessions: {e}")
        
        # Reset timers
        self._storing_session_timer = time.time() + STORE_SESSION_TIMEOUT
        self._touched_sessions = 0
    
    def _restore_sessions(self) -> Dict[str, 'Session']:
        """
        Restore sessions from persistent storage.
        
        Loads previously saved sessions from disk and recreates
        Session objects. Expired sessions are automatically discarded.
        
        Returns:
            Dictionary of active sessions keyed by remote ID
        """
        sessions = {}
        
        try:
            storage = self.getStorage()
            datas = storage.restore(name='Sessions')
            
            if not isinstance(datas, dict):
                datas = {}
            
            # Import Session class
            from ..http.session import Session
            
            # Recreate session objects from stored data
            restored_count = 0
            expired_count = 0
            
            for remoteid, data in datas.items():
                if not (remoteid and isinstance(data, dict)):
                    continue
                
                try:
                    # Create session from stored data
                    session = Session(
                        logger=self.logger,
                        timer=data.get('timer'),
                        nonce=data.get('nonce'),
                        sid=remoteid,
                        infos=data.get('infos'),
                        **{k: v for k, v in data.items() if k.startswith('_')}
                    )
                    
                    # Skip expired sessions
                    if not session.expired():
                        sessions[remoteid] = session
                        restored_count += 1
                    else:
                        expired_count += 1
                
                except Exception as e:
                    if self.logger:
                        self.logger.error(
                            f"Failed to restore session {remoteid}: {e}"
                        )
            
            if self.logger:
                self.logger.debug(
                    f"Restored {restored_count} sessions "
                    f"({expired_count} expired sessions discarded)"
                )
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to restore sessions: {e}")
        
        return sessions
    
    def keep_sessions(self) -> float:
        """
        Clean expired sessions and store active ones.
        
        Performs periodic maintenance:
        1. Removes expired sessions
        2. Stores active sessions to disk
        
        Returns:
            Timestamp of next scheduled session storage
        """
        # Lazy load sessions
        if not self.sessions:
            self.sessions = self._restore_sessions()
        
        # Find and remove expired sessions
        expired_sessions = []
        for remoteid, session in self.sessions.items():
            if session.expired():
                expired_sessions.append(remoteid)
        
        for remoteid in expired_sessions:
            if remoteid in self.sessions:
                del self.sessions[remoteid]
                self._touched_sessions += 1
        
        if expired_sessions and self.logger:
            self.logger.debug(f"Removed {len(expired_sessions)} expired sessions")
        
        # Store remaining sessions
        self._store_sessions()
        
        return self._storing_session_timer
    
    def sessions_dict(self) -> Optional[Dict[str, 'Session']]:
        """
        Get sessions dictionary if not empty.
        
        Returns:
            Dictionary of sessions, or None if no active sessions
        """
        # Lazy load sessions
        if not self.sessions:
            self.sessions = self._restore_sessions()
        
        return self.sessions if self.sessions else None
    
    def __del__(self):
        """
        Destructor - ensure sessions are stored when object is destroyed.
        
        Called when the ListenerTarget instance is garbage collected.
        Ensures all session data is persisted before cleanup.
        """
        if hasattr(self, '_storing_session_timer'):
            # Force immediate storage
            self._storing_session_timer = time.time()
            self._store_sessions()


# Module cleanup function
def _cleanup_listener():
    """
    Store sessions on module cleanup.
    
    Registered with atexit to ensure sessions are saved
    when the Python interpreter shuts down.
    """
    global _listener
    if _listener and hasattr(_listener, '_storing_session_timer'):
        _listener._storing_session_timer = time.time()
        _listener._store_sessions()


# Register cleanup function to run on exit
atexit.register(_cleanup_listener)