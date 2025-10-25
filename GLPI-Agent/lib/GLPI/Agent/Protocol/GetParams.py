"""
GLPI::Agent::Protocol::GetParams - GetParams GLPI Agent messages

This is a class to handle GetParams protocol messages.
"""

from GLPI.Agent.Protocol.Message import ProtocolMessage
from GLPI.Agent.Version import PROVIDER, VERSION


class GetParams(ProtocolMessage):
    """
    GetParams protocol message handler.
    
    Handles get_params messages sent to and received from the GLPI server.
    """
    
    def __init__(self, **params):
        """
        Initialize get_params message.
        
        Args:
            **params: Parameters including:
                - params_id: Parameters identifier
                - use: Usage context
                - deviceid: Device identifier
                - message: Message content
                - logger: Logger instance
        """
        # Set supported params
        params['supported_params'] = ['params_id', 'use', 'deviceid']
        
        super().__init__(**params)
        
        # Setup request with action for this message if it's not a server answer
        if not self.get('status'):
            message = self.get()
            message['action'] = 'get_params'
            message['name'] = f"{PROVIDER}-Agent"
            message['version'] = VERSION
    
    def is_valid_message(self):
        """
        Check if get_params message is valid.
        
        Message from server CAN contain:
        - a simple 'credentials' array
        
        Returns:
            True if valid message
        """
        if self.get() is None:
            return False
        
        status = self.get('status') or 'ok'
        if status == 'error':
            return True
        
        # Message from server CAN contain a 'credentials' array
        credentials = self.get('credentials')
        if isinstance(credentials, list):
            return True
        
        return False
