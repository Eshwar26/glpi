"""
GLPI Agent HTTP Server Plugins

This package contains plugins for the embedded HTTP server.
Plugins handle specific types of requests and provide functionality
such as inventory, proxy, SSL, authentication, and toolbox features.
"""

__all__ = [
    'Plugin',
    'BasicAuthentication',
    'Inventory',
    'Proxy',
    'SecondaryProxy',
    'SSL',
    'Test',
    'ToolBox',
]

