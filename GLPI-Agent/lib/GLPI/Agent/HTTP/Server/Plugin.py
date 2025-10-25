"""
GLPI Agent HTTP Server Plugin Base Class

This module provides the base class for HTTP server plugins.
Plugins handle specific request types for the embedded HTTP server.
"""

import os
import re
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse

try:
    from GLPI.Agent.Config import Config
except ImportError:
    Config = object

from GLPI.Agent.Logger import Logger
from GLPI.Agent import Version


class Plugin(Config if Config != object else object):
    """
    Base class template for embedded HTTP server plugins.
    
    Plugins handle specific requests on the HTTP server.
    They can have their own configuration files and ports.
    """

    def __init__(self, **params):
        """
        Initialize the plugin.
        
        Args:
            **params: Parameters including:
                - server: Associated server instance
        """
        # Get plugin name from class name
        class_name = self.__class__.__name__
        
        self.logger = (params.get('server', {}).get('logger') if 
                      isinstance(params.get('server'), dict) else
                      getattr(params.get('server'), 'logger', None)) or Logger()
        
        self.server = params.get('server')
        self.name_value = class_name
        
        # Import _confdir from agent configuration
        if self.server:
            if hasattr(self.server, 'agent'):
                agent = self.server.agent
                if hasattr(agent, 'config') and hasattr(agent.config, '_confdir'):
                    self._confdir = agent.config._confdir
        
        # Check and set _confdir
        if not hasattr(self, '_confdir') or not self._confdir or not os.path.isdir(self._confdir):
            # Set absolute confdir from default or search from current path
            search_paths = ['./etc', '../etc', '../../etc']
            found_dir = None
            
            for path in search_paths:
                if os.path.isdir(path):
                    found_dir = path
                    break
            
            if found_dir:
                self._confdir = os.path.abspath(found_dir)
            else:
                self._confdir = getattr(self, '_confdir', None)
                if self._confdir:
                    self._confdir = os.path.abspath(self._confdir)
        
        # Handle defaults
        self._default = self.defaults()
        
        # Initialize parent if available
        if Config != object:
            super().__init__(**params)

    def init(self):
        """
        Initialize the plugin.
        
        Loads configuration from file if available and
        sets up plugin-specific configurations.
        """
        # Get version
        version = getattr(self.__class__, 'VERSION', Version.VERSION)
        
        self.debug(f"Initializing {self.name_value} v{version} Server plugin...")
        
        # Load defaults
        defaults = self.defaults()
        for param, value in defaults.items():
            setattr(self, param, value)
        
        # Load configuration file if available
        if self.confdir() and self.config_file():
            config_path = os.path.join(self.confdir(), self.config_file())
            if os.path.isfile(config_path) and os.access(config_path, os.R_OK):
                self.debug(f"Loading {self.name_value} Server plugin configuration from {config_path}")
                # Load configuration file
                if hasattr(self, 'loadFromFile'):
                    self.loadFromFile(file=config_path, defaults=defaults)
            else:
                self.debug(f"{self.name_value} Server plugin configuration missing: {config_path}")
        
        # Handle forbid_not_trusted option
        forbid_not_trusted = self.config("forbid_not_trusted")
        if forbid_not_trusted is not None:
            self.forbid_not_trusted_value = (
                0 if re.match(r'^0|no$', str(forbid_not_trusted), re.IGNORECASE) 
                else 1
            )
        else:
            self.forbid_not_trusted_value = 0

    def priority(self) -> int:
        """
        Get plugin priority.
        
        Plugins with greater priority values are used first.
        
        Returns:
            Priority value (default: 10)
        """
        return 10

    def name(self) -> str:
        """
        Get the plugin name.
        
        Returns:
            Plugin name
        """
        return self.name_value

    def defaults(self) -> Dict[str, Any]:
        """
        Get default configuration values.
        
        Must return a key-value dict if a config file is to be read.
        
        Returns:
            Dictionary of default values
        """
        return {}

    def url(self, request) -> Optional[str]:
        """
        Get the URL for this plugin.
        
        Args:
            request: HTTP request object
            
        Returns:
            Plugin URL or None
        """
        defaults = self.defaults()
        if 'url_path' not in defaults:
            return None
        
        # Extract scheme from request URI type
        uri = request.uri() if hasattr(request, 'uri') else None
        if not uri:
            return None
        
        uri_type = type(uri).__name__
        match = re.search(r'URI::(.+)', uri_type)
        if not match:
            return None
        
        scheme = match.group(1)
        if not scheme or not scheme.startswith('http'):
            return None
        
        path = self.config('url_path') or defaults.get('url_path')
        host = request.header('host') if hasattr(request, 'header') else None
        
        if not host:
            return None
        
        url = f"{scheme}://{host}{path}"
        
        # Add port if configured
        port = self.port()
        if port:
            parsed = urlparse(url)
            url = f"{parsed.scheme}://{parsed.hostname}:{port}{parsed.path}"
        
        return url

    def supported_method(self, method: str) -> bool:
        """
        Check if request method is supported.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            
        Returns:
            True if supported, False otherwise
        """
        if method == 'GET':
            return True
        
        self.error(f"invalid request type: {method}")
        return False

    def port(self) -> int:
        """
        Get the configured port for this plugin.
        
        Returns:
            Port number or 0 to use default
        """
        port = getattr(self, 'port_value', None)
        if port and isinstance(port, int) and 0 < port < 65536:
            return port
        return 0

    def disabled(self) -> bool:
        """
        Check if plugin is disabled.
        
        Returns:
            True if disabled, False otherwise
        """
        disabled = getattr(self, 'disabled_value', None)
        if disabled and not re.match(r'^0|no$', str(disabled), re.IGNORECASE):
            return True
        return False

    def disable(self, reason: Optional[str] = None):
        """
        Disable the plugin.
        
        Args:
            reason: Optional reason for disabling
        """
        self.disabled_value = True
        self.info(reason or "plugin disabled")

    def log_prefix(self) -> str:
        """
        Get the log prefix for this plugin.
        
        Returns:
            Log prefix string
        """
        return "[http server plugin] "

    def error(self, message: str):
        """
        Log an error message.
        
        Args:
            message: Error message
        """
        if self.logger:
            self.logger.error(self.log_prefix() + message)

    def info(self, message: str):
        """
        Log an info message.
        
        Args:
            message: Info message
        """
        if self.logger:
            self.logger.info(self.log_prefix() + message)

    def debug(self, message: str):
        """
        Log a debug message.
        
        Args:
            message: Debug message
        """
        if self.logger:
            self.logger.debug(self.log_prefix() + message)

    def debug2(self, message: str):
        """
        Log a detailed debug message.
        
        Args:
            message: Debug message
        """
        if self.logger:
            self.logger.debug2(self.log_prefix() + message)

    def config(self, name: str, value: Any = None) -> Any:
        """
        Get or set a configuration value.
        
        Args:
            name: Configuration name
            value: Optional value to set
            
        Returns:
            Configuration value
        """
        if value is not None:
            setattr(self, name, value)
        return getattr(self, name, None)

    def forbid_not_trusted(self) -> bool:
        """
        Check if non-trusted clients are forbidden.
        
        Returns:
            True if non-trusted clients should be rejected
        """
        return getattr(self, 'forbid_not_trusted_value', False)

    def confdir(self) -> Optional[str]:
        """
        Get the configuration directory.
        
        Returns:
            Configuration directory path
        """
        return getattr(self, '_confdir', None)

    def config_file(self) -> Optional[str]:
        """
        Get the configuration filename.
        
        Override in subclasses to provide config file name.
        
        Returns:
            Configuration filename or None
        """
        return None

    def urlMatch(self, path: str) -> bool:
        """
        Check if URL path matches this plugin.
        
        Override in subclasses to provide URL matching logic.
        
        Args:
            path: URL path
            
        Returns:
            True if path matches, False otherwise
        """
        return False

    def handle(self, client, request, client_ip: str) -> int:
        """
        Handle an HTTP request.
        
        Override in subclasses to handle requests.
        
        Args:
            client: Client connection
            request: HTTP request object
            client_ip: Client IP address
            
        Returns:
            HTTP status code
        """
        return 404

    def timer_event(self) -> Optional[int]:
        """
        Handle timer events.
        
        Override in subclasses to support timer events.
        
        Returns:
            Next timer timeout (in seconds) or None
        """
        return None

    def rate_limited(self, client_ip: str) -> bool:
        """
        Check if request rate limit has been reached.
        
        Args:
            client_ip: Client IP address
            
        Returns:
            True if rate limited, False otherwise
        """
        import time
        
        maxrate = self.config('maxrate')
        maxrate_period = self.config('maxrate_period') or 3600
        
        if not client_ip or not maxrate:
            return False
        
        now = time.time()
        
        # Initialize rate limitation tracking
        if not hasattr(self, '_rate_limitation'):
            self._rate_limitation = {}
        
        if client_ip not in self._rate_limitation:
            self._rate_limitation[client_ip] = []
        
        tries = self._rate_limitation[client_ip]
        
        # Cleanup old tries
        while tries and tries[0] < now - maxrate_period:
            tries.pop(0)
        
        # Keep try timestamp unless still limited and in the same second
        if not (len(tries) > maxrate and tries[-1] == now):
            tries.append(now)
        
        if len(tries) > maxrate:
            limit_log = getattr(self, '_rate_limitation_log', 0)
            # Also limit logging on heavy load
            if limit_log < now - 10:
                self.info(f"request rate limitation applied for remote {client_ip}")
                if hasattr(self, '_rate_limitation_log_filter') and self._rate_limitation_log_filter:
                    self.info(f"{self._rate_limitation_log_filter} limited requests not logged")
                self._rate_limitation_log_filter = 0
                self._rate_limitation_log = now
            else:
                self._rate_limitation_log_filter = getattr(self, '_rate_limitation_log_filter', 0) + 1
            return True
        
        return False

