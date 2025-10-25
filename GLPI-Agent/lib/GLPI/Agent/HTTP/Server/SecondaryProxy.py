"""
GLPI Agent HTTP Server Secondary Proxy Plugin

Provides a secondary proxy service, useful for opening
a proxy on different ports or with SSL support.
"""

try:
    from GLPI.Agent.HTTP.Server.Proxy import Proxy
except ImportError:
    from GLPI.Agent.HTTP.Server.Plugin import Plugin as Proxy


VERSION = "1.1"


class SecondaryProxy(Proxy):
    """
    Secondary proxy server plugin.
    
    Inherits all functionality from the main Proxy plugin
    but uses a different configuration file.
    """

    def log_prefix(self) -> str:
        """Get the log prefix for this plugin."""
        return "[proxy2 server plugin] "

    def config_file(self) -> str:
        """Get the configuration filename."""
        return "proxy2-server-plugin.cfg"

