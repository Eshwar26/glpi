# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node
import base64
import re

class Stream(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::Stream
    WSMan Stream node handling with base64 decoding.
    """
    xmlns = 'rsp'
    
    def __init__(self, streams):
        """
        Initialize a Stream node with stream data.
        
        Args:
            streams: Either a single stream dict or a list of stream dicts
        """
        # Ensure streams is a list
        if not isinstance(streams, list):
            streams = [streams]
        
        # Initialize storage dictionary
        stream_data = {}
        
        for stream in streams:
            # Skip if not a dictionary
            if not isinstance(stream, dict):
                continue
            
            # Get CommandId
            cid = stream.get('-CommandId')
            if not cid:
                continue
            
            # Get Name
            name = stream.get('-Name')
            if not name:
                continue
            
            # Only process stdout or stderr
            if not re.match(r'^std(out|err)$', name):
                continue
            
            # Initialize nested dict if needed
            if cid not in stream_data:
                stream_data[cid] = {}
            
            # Decode and append base64 text if present
            text = stream.get('#text')
            if text is not None and len(text) > 0:
                decoded_text = base64.b64decode(text).decode('utf-8', errors='replace')
                if name not in stream_data[cid]:
                    stream_data[cid][name] = ''
                stream_data[cid][name] += decoded_text
            
            # Handle End flag
            end_flag = stream.get('-End')
            if end_flag:
                if re.match(r'^true$', end_flag, re.IGNORECASE):
                    stream_data[cid][f"_end_{name}"] = True
        
        # Store the stream data as instance attributes
        self._stream_data = stream_data
        
        # Call parent constructor (though this class doesn't use typical Node structure)
        super().__init__()
    
    def stdout(self, cid):
        """
        Get stdout content for a command ID.
        
        Args:
            cid: The Command ID
            
        Returns:
            str: The stdout content, or empty string if not found
        """
        if cid not in self._stream_data:
            return None
        
        return self._stream_data[cid].get('stdout', '')
    
    def stderr(self, cid):
        """
        Get stderr content for a command ID.
        
        Args:
            cid: The Command ID
            
        Returns:
            str: The stderr content, or empty string if not found
        """
        if cid not in self._stream_data:
            return None
        
        return self._stream_data[cid].get('stderr', '')
    
    def stdout_is_full(self, cid):
        """
        Check if stdout stream is complete for a command ID.
        
        Args:
            cid: The Command ID
            
        Returns:
            bool or int: True/1 if complete, False/0 otherwise, or None if cid not found
        """
        if cid not in self._stream_data:
            return None
        
        return self._stream_data[cid].get('_end_stdout', 0)
    
    def stderr_is_full(self, cid):
        """
        Check if stderr stream is complete for a command ID.
        
        Args:
            cid: The Command ID
            
        Returns:
            bool or int: True/1 if complete, False/0 otherwise, or None if cid not found
        """
        if cid not in self._stream_data:
            return None
        
        return self._stream_data[cid].get('_end_stderr', 0)


# Note: The package structure is handled by module imports.
# xmlns is a class attribute.