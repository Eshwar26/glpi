"""
GLPI::Agent::Protocol::Answer - Answer for GLPI Agent messages

This is a class to handle answer protocol messages.
"""

import json

from GLPI.Agent.Protocol.Message import ProtocolMessage


class Answer(ProtocolMessage):
    """
    Answer protocol message handler.
    
    Handles answer messages sent from the GLPI server.
    """
    
    def __init__(self, httpcode=200, httpstatus='OK', agentid='', proxyids='', **params):
        """
        Initialize answer message.
        
        Args:
            httpcode (int): HTTP status code (default: 200)
            httpstatus (str): HTTP status text (default: 'OK')
            agentid (str): Agent identifier
            proxyids (str): Proxy identifiers
            **params: Additional parameters including:
                - status: Message status
                - expiration: Expiration time
                - message: Message content
        """
        # Set supported params
        params['supported_params'] = ['status', 'expiration']
        
        super().__init__(**params)
        
        self._http_code = httpcode
        self._http_status = httpstatus
        self._agentid = agentid
        self._proxyids = proxyids
        
        # Handle case message was a dump
        for key in ['_http_code', '_http_status', '_agentid', '_proxyids']:
            value = self.delete(key)
            if value:
                setattr(self, key, value)
    
    def error(self, error):
        """
        Update the message with a status error.
        
        Args:
            error (str): Error message
        """
        if error is None:
            return
        
        self._message['status'] = 'error'
        self._message['message'] = error
        self._message.pop('expiration', None)
        
        # Returning an error message is still a good HTTP message
        self._http_code = 200
        self._http_status = 'OK'
    
    def content_type(self):
        """
        Get content type for HTTP response.
        
        Returns:
            Content type string
        """
        return 'application/json'
    
    def http_code(self):
        """
        Get HTTP status code.
        
        Returns:
            HTTP status code
        """
        return self._http_code
    
    def http_status(self):
        """
        Get HTTP status text.
        
        Returns:
            HTTP status text
        """
        return self._http_status
    
    def agentid(self):
        """
        Get agent ID.
        
        Returns:
            Agent ID string
        """
        return self._agentid
    
    def proxyid(self):
        """
        Get proxy IDs.
        
        Returns:
            Proxy IDs string
        """
        return self._proxyids
    
    def dump(self):
        """
        Dump message including HTTP metadata.
        
        Returns:
            JSON string with message and metadata
        """
        dump_dict = {key: value for key, value in self._message.items()}
        dump_dict['_http_code'] = self._http_code
        dump_dict['_http_status'] = self._http_status
        dump_dict['_agentid'] = self._agentid
        dump_dict['_proxyids'] = self._proxyids
        
        return json.dumps(dump_dict, ensure_ascii=False)
    
    def success(self):
        """Update message to indicate success."""
        self._http_code = 200
        self._http_status = 'OK'
        if self.status() == 'pending':
            self._message['status'] = 'ok'
