# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node

class OutputStreams(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::OutputStreams
    WSMan OutputStreams node handling.
    """
    xmlns = 'rsp'
    
    def __init__(self):
        """
        Initialize an OutputStreams node with default stdout and stderr streams.
        """
        # Call parent constructor with stream specification
        super().__init__("stdout stderr")


# Note: The package structure is handled by module imports.
# xmlns is a class attribute.