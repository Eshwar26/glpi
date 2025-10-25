"""
GLPI::Agent::Protocol::Contact - Contact GLPI Agent messages

This is a class to handle Contact protocol messages.
"""

from GLPI.Agent.Protocol.Message import ProtocolMessage
from GLPI.Agent.Version import PROVIDER, VERSION


class Contact(ProtocolMessage):
    """
    Contact protocol message handler.
    
    Handles contact messages sent to and received from the GLPI server.
    """
    
    def __init__(self, **params):
        """
        Initialize contact message.
        
        Args:
            **params: Parameters including:
                - deviceid: Device identifier
                - installed_tasks: List of installed tasks
                - enabled_tasks: List of enabled tasks
                - httpd_plugins: List of HTTP plugins
                - httpd_port: HTTP daemon port
                - tag: Asset tag
                - tasks: Task list
                - message: Message content
                - logger: Logger instance
        """
        # Normalize parameter names (Perl used hyphens, Python uses underscores)
        normalized_params = params.copy()
        if 'installed-tasks' in params:
            normalized_params['installed_tasks'] = params.pop('installed-tasks')
        if 'enabled-tasks' in params:
            normalized_params['enabled_tasks'] = params.pop('enabled-tasks')
        if 'httpd-plugins' in params:
            normalized_params['httpd_plugins'] = params.pop('httpd-plugins')
        if 'httpd-port' in params:
            normalized_params['httpd_port'] = params.pop('httpd-port')
        
        # Set supported params
        normalized_params['supported_params'] = [
            'deviceid', 'installed_tasks', 'enabled_tasks',
            'httpd_plugins', 'httpd_port', 'tag', 'tasks'
        ]
        
        super().__init__(**normalized_params)
        
        # Setup request with action for this message if it's not a server answer
        if not self.get('status'):
            message = self.get()
            message['action'] = 'contact'
            message['name'] = f"{PROVIDER}-Agent"
            message['version'] = VERSION
    
    def is_valid_message(self):
        """
        Check if contact message is valid.
        
        CONTACT message from server MUST contain:
        - a status
        - a valid expiration greater than 0
        
        Returns:
            True if valid message
        """
        if not super().is_valid_message():
            return False
        
        return self.expiration() > 0
