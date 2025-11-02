# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node
# from glpi.agent.soap.wsman.attribute import Attribute
# from glpi.agent.soap.wsman.shell import Shell
# from glpi.agent.soap.wsman.desired_stream import DesiredStream

class Receive(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::Receive
    WSMan Receive node handling.
    """
    xmlns = 'rsp'
    
    def __init__(self, cid):
        """
        Initialize a Receive node with command ID.
        
        Args:
            cid: The Command ID
        """
        # Call parent constructor with attributes and DesiredStream
        super().__init__(
            Attribute(**{f"xmlns:{Shell.xmlns}": Shell.xsd}),
            Attribute(SequenceId=0),
            DesiredStream(cid)
        )


# Note: The package structure is handled by module imports.
# xmlns is a class attribute.