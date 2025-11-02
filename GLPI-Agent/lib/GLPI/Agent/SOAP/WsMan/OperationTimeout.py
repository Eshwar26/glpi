# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node

class OperationTimeout(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::OperationTimeout
    WSMan OperationTimeout node handling.
    """
    xmlns = 'w'
    
    def __init__(self, timeout):
        """
        Initialize an OperationTimeout node with a timeout value.
        
        Args:
            timeout: The timeout value in seconds (can be float)
        """
        # Format timeout as ISO 8601 duration format (PT[seconds]S)
        formatted_timeout = f"PT{timeout:.3f}S"
        
        # Call parent constructor with formatted timeout string
        super().__init__(formatted_timeout)


# Note: The package structure is handled by module imports.
# xmlns is a class attribute.