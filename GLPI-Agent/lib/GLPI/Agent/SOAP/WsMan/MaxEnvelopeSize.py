# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node
# from glpi.agent.soap.wsman.attribute import Attribute

class MaxEnvelopeSize(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::MaxEnvelopeSize
    WSMan MaxEnvelopeSize node handling.
    """
    xmlns = 'w'
    
    def __init__(self, size):
        """
        Initialize a MaxEnvelopeSize node with a size value.
        
        Args:
            size: The maximum envelope size value
        """
        # Call parent constructor with must_understand attribute and size
        super().__init__(
            Attribute.must_understand(),
            size
        )


# Note: The package structure is handled by module imports.
# xmlns is a class attribute.