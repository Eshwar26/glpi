# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node
# from glpi.agent.soap.wsman.attribute import Attribute

class DesiredStream(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::DesiredStream
    WSMan DesiredStream node handling.
    """
    xmlns = 'rsp'
    
    def __init__(self, cid):
        """
        Initialize a DesiredStream node with CommandId and stream specification.
        
        Args:
            cid: The Command ID
        """
        # Call parent constructor with Attribute and stream specification
        super().__init__(
            Attribute(CommandId=cid),
            "stdout stderr"
        )


# Note: The package structure is handled by module imports.
# xmlns is a class attribute.