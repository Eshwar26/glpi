"""
GLPI Agent HTTP Server SSL Plugin

Provides SSL/TLS support for HTTP server on configured ports.
"""

import os
import ssl
from pathlib import Path
from typing import Optional, List

from GLPI.Agent.HTTP.Server.Plugin import Plugin


VERSION = "1.2"


class SSL(Plugin):
    """
    SSL server plugin for HTTPS support.
    
    Enables SSL/TLS encryption on configured ports.
    Requires certificate and key files.
    """

    def log_prefix(self) -> str:
        """Get the log prefix for this plugin."""
        return "[ssl server plugin] "

    def config_file(self) -> str:
        """Get the configuration filename."""
        return "ssl-server-plugin.cfg"

    def defaults(self) -> dict:
        """
        Get default configuration values.
        
        Returns:
            Dictionary of defaults
        """
        return {
            'disabled': "yes",
            'ports': 0,
            # SSL support
            'ssl_cert_file': None,
            'ssl_key_file': None,
            'ssl_cipher': None,
            'forbid_not_trusted': "no",
        }

    def init(self):
        """Initialize the SSL plugin and validate configuration."""
        super().init()
        
        # Don't verify SSL configuration if disabled
        if self.disabled():
            return
        
        # Get absolute canonical paths
        if self.config('ssl_cert_file'):
            self.cert_file = os.path.abspath(
                os.path.join(self.confdir(), self.config('ssl_cert_file'))
            )
        else:
            self.cert_file = None
        
        if self.config('ssl_key_file'):
            self.key_file = os.path.abspath(
                os.path.join(self.confdir(), self.config('ssl_key_file'))
            )
        else:
            self.key_file = None
        
        if self.config('ssl_cipher'):
            self.cipher = self.config('ssl_cipher')
        else:
            self.cipher = None
        
        # Check certificate file is set
        if not self.cert_file:
            self.error("Plugin enabled without certificate file set in configuration")
            self.disable("Plugin disabled on wrong configuration")
            return
        
        # Check certificate file exists
        if not os.path.exists(self.cert_file):
            self.error(f"Plugin enabled but {self.cert_file} certificate file is missing")
            self.disable("Plugin disabled on wrong configuration")
            return
        
        # Check key file exists if set
        if self.key_file and not os.path.exists(self.key_file):
            self.error(f"Plugin enabled but {self.key_file} key file is missing")
            self.disable("Plugin disabled on wrong configuration")
            return
        
        # If key file is missing, assume it's included in cert file
        if not self.key_file:
            self.key_file = self.cert_file
        
        # Setup ports as a list
        ports_str = str(self.config('ports') or '0')
        self.ports = [
            int(p) for p in ports_str.split(',') 
            if p.strip() and int(p) < 65536
        ]
        
        # Try to load SSL module
        try:
            import ssl as ssl_module
            self.ssl_available = True
        except ImportError as e:
            self.error(f"HTTPD can't load SSL support: {e}")
            self.disable("Plugin disabled on wrong configuration")
            return
        
        self.debug2(f"Certificate file: {self.cert_file}")
        self.debug2(f"Key file:         {self.key_file}")
        self.debug2(f"Cipher:           {self.cipher or 'n/a'}")
        
        # Check if debug is enabled
        debug_ssl = False
        if hasattr(self, 'logger') and hasattr(self.logger, 'backends'):
            if isinstance(self.logger.backends, list):
                debug_ssl = any(
                    'Stderr' in type(b).__name__ 
                    for b in self.logger.backends
                )
        
        # Enable SSL debugging if needed
        if debug_ssl and hasattr(self.logger, 'debug_level'):
            if self.logger.debug_level() >= 2:
                # Enable SSL debug logging
                ssl.PROTOCOL_TLS
    
    def upgrade_SSL(self, client) -> Optional[object]:
        """
        Upgrade a client connection to SSL.
        
        Args:
            client: Client connection to upgrade
            
        Returns:
            SSL-wrapped client or None on failure
        """
        try:
            # Create SSL context
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(
                certfile=self.cert_file,
                keyfile=self.key_file
            )
            
            # Set cipher if configured
            if self.cipher:
                context.set_ciphers(self.cipher)
            
            # Wrap the socket
            ssl_client = context.wrap_socket(
                client,
                server_side=True
            )
            
            self.debug("HTTPD started new SSL session")
            return ssl_client
            
        except Exception as e:
            self.debug(f"HTTPD can't start SSL session: {e}")
            if hasattr(client, 'close'):
                client.close()
            return None


class ClientConnSSL:
    """
    SSL-wrapped client connection.
    
    This is a helper class for managing SSL client connections.
    """
    
    def __init__(self, client, plugin):
        """
        Initialize SSL client connection.
        
        Args:
            client: Base client connection
            plugin: SSL plugin instance
        """
        self.client = client
        self.plugin = plugin
        self._ssl_no_shutdown = False
    
    def close(self, ssl_no_shutdown: bool = None):
        """
        Close the connection.
        
        Args:
            ssl_no_shutdown: If True, don't shutdown SSL
        """
        if ssl_no_shutdown is None:
            ssl_no_shutdown = self._ssl_no_shutdown
        
        if not ssl_no_shutdown and hasattr(self.client, 'unwrap'):
            try:
                self.client.unwrap()
            except:
                pass
        
        if hasattr(self.client, 'close'):
            self.client.close()
    
    def no_ssl_shutdown(self, flag: bool):
        """
        Set whether to skip SSL shutdown on close.
        
        Args:
            flag: True to skip SSL shutdown
        """
        self._ssl_no_shutdown = flag
    
    def __getattr__(self, name):
        """Delegate attribute access to wrapped client."""
        return getattr(self.client, name)

