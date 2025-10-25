"""
GLPI Agent Task Deploy UserCheck Module

User interaction check for deployment tasks.
"""

import platform
from typing import Dict, List, Optional, Any


# Supported UserCheck modules by platform
SUPPORTED_USERCHECK_MODULES = {
    'Windows': 'WTS'
}

# Supported platform keys
SUPPORTED_PLATFORM_KEYS = {
    'win32': 'Windows',
    'macos': 'Darwin',
    'linux': 'Linux',
    'any': 'ALL',
    'none': 'None'
}

# Supported configuration keys
SUPPORTED_KEYS = [
    'type', 'text', 'title', 'icon', 'buttons', 'timeout', 'wait', 'platform',
    'on_ok', 'on_cancel', 'on_yes', 'on_no', 'on_retry', 'on_tryagain', 'on_abort',
    'on_timeout', 'on_nouser', 'on_multiusers', 'on_ignore', 'on_async'
]


class UserCheck:
    """User interaction check handler"""
    
    def __init__(self, logger=None, check=None):
        """
        Initialize UserCheck.
        
        Args:
            logger: Logger instance
            check: Check configuration dictionary
        """
        self.logger = logger
        self.type = 'after'
        self.platform = 'any'
        self._stopped = False
        self._on_event = None
        self._events = []
        self.user = None
        
        # Default event definitions
        self._on_error = 'stop:stop:agent_failure'
        self._on_none = 'stop:stop:error_no_event'
        self._on_nouser = 'continue:continue:'
        self._on_multiusers = 'ask:continue:'
        
        # Check platform support
        system = platform.system()
        if system not in SUPPORTED_USERCHECK_MODULES:
            self.debug(f"user interaction not supported on {system} platform")
            return
        
        # Load check parameters
        if check and isinstance(check, dict):
            for key in SUPPORTED_KEYS:
                if key not in check:
                    continue
                
                if key.startswith('on_'):
                    # Keep event values as private
                    setattr(self, f'_{key}', check[key])
                else:
                    setattr(self, key, check[key])
        
        # Check if we are on a requested platform
        requested_platforms = [
            SUPPORTED_PLATFORM_KEYS.get(p.lower(), 'None')
            for p in self.platform.split(',')
        ]
        
        if 'ALL' not in requested_platforms and system not in requested_platforms:
            self.debug(
                f"user interaction requested on '{self.platform}', " +
                f"not on this {system} platform"
            )
            return
    
    def tagged(self, message: str) -> str:
        """Tag a message with usercheck type"""
        return f"usercheck {self.type}: {message}"
    
    def debug(self, message: str) -> None:
        """Log debug message"""
        if self.logger:
            self.logger.debug(self.tagged(message))
    
    def debug2(self, message: str) -> None:
        """Log debug2 message"""
        if self.logger and hasattr(self.logger, 'debug2'):
            self.logger.debug2(self.tagged(message))
    
    def error(self, message: str) -> None:
        """Log error message"""
        if self.logger:
            self.logger.error(self.tagged(message))
    
    def handle_event(self, event: str, message: str = None) -> bool:
        """
        Handle a user event.
        
        Args:
            event: Event name (e.g., 'on_ok', 'on_cancel')
            message: Optional message
        
        Returns:
            True to stop processing, False to continue
        """
        if message:
            self.debug(message)
        
        policy_attr = f'_{event}'
        policy = getattr(self, policy_attr, None)
        
        if policy is not None:
            self.debug2(f"{event} event: applying policy: {policy}")
        else:
            policy = "stop:error_bad_event"
            self.error(f"Unsupported {event} event: setting policy to {policy}")
            setattr(self, policy_attr, policy)
        
        # Store event
        self._on_event = event
        self._events.append(self.userevent())
        
        # Check policy action
        if policy.startswith('continue:'):
            return self.do_continue()
        elif policy.startswith('ask:'):
            return self.ask_user()
        else:  # stop
            return self.stop()
    
    def do_continue(self) -> bool:
        """Continue processing"""
        return False
    
    def ask_user(self) -> bool:
        """Ask user for input"""
        # Override in subclass
        return False
    
    def stop(self) -> bool:
        """Stop processing"""
        self._stopped = True
        return True
    
    def stopped(self) -> bool:
        """Check if processing is stopped"""
        return self._stopped
    
    def set_user(self, user: str) -> None:
        """Set current user"""
        self.user = user
    
    def userevent(self) -> Dict[str, Any]:
        """
        Get user event information for server.
        
        Returns:
            Dictionary with event information
        """
        event = {}
        
        if self._on_event:
            # Remove 'on_' prefix
            event['name'] = self._on_event[3:] if self._on_event.startswith('on_') else self._on_event
        
        if self.user:
            event['user'] = self.user
        
        policy = getattr(self, f'_{self._on_event}', '') if self._on_event else ''
        if policy:
            parts = policy.split(':')
            if len(parts) >= 3:
                event['status'] = parts[2]
        
        return event
    
    def status_for_server(self) -> Dict[str, Any]:
        """
        Get status information for server.
        
        Returns:
            Dictionary with status information
        """
        return {
            'events': self._events
        }
    
    def tell_users(self) -> None:
        """Tell users - override in subclass"""
        pass
    
    def always_ask_users(self) -> bool:
        """Check if all users should be asked"""
        # Override in subclass if needed
        return False
