# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node
import uuid
import re

class MessageID(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::MessageID
    WSMan MessageID node handling with UUID generation.
    """
    xmlns = 'a'
    
    def __init__(self, messageid=None):
        """
        Initialize a MessageID node with an optional message ID or generate a UUID.
        
        Args:
            messageid: Optional message ID string. If not provided, a UUID is generated.
        """
        if messageid:
            # If messageid is provided, use it directly
            super().__init__(messageid)
            self._uuid = None
        else:
            # Generate a new UUID
            generated_uuid = str(uuid.uuid4())
            super().__init__(f"uuid:{generated_uuid}")
            self._uuid = generated_uuid
    
    def uuid(self):
        """
        Get the UUID from the MessageID.
        
        Returns:
            str or None: The UUID string, or None if not found
        """
        # Try to extract UUID from the string representation
        string_value = self.string()
        match = re.match(r'^uuid:(.*)$', string_value) if string_value else None
        extracted_uuid = match.group(1) if match else None
        
        # Return None if neither stored nor extracted UUID exists
        if not self._uuid and not extracted_uuid:
            return None
        
        # Return stored UUID if available
        if self._uuid:
            return self._uuid
        
        # Cache and return extracted UUID
        self._uuid = extracted_uuid
        return self._uuid
    
    def reset_uuid(self):
        """
        Generate and set a new UUID for the MessageID.
        
        Returns:
            str: The new UUID string in "uuid:..." format
        """
        generated_uuid = str(uuid.uuid4())
        self._uuid = generated_uuid
        
        return self.string(f"uuid:{generated_uuid}")


# Note: The package structure is handled by module imports.
# xmlns is a class attribute.