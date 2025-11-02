# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node
# from glpi.agent.soap.wsman.attribute import Attribute

class Option(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::Option
    WSMan Option node handling.
    """
    xmlns = 'w'
    
    def __init__(self, name, text):
        """
        Initialize an Option node with a name attribute and text content.
        
        Args:
            name: The name attribute value
            text: The text content of the option
        """
        # Call parent constructor with Attribute and text
        super().__init__(
            Attribute(Name=name),
            text
        )


# Note: The package structure is handled by module imports.
# xmlns is a class attribute.