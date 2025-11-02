# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node
# from glpi.agent.soap.wsman.attribute import Attribute

class Filter(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::Filter
    WSMan Filter node handling.
    """
    xmlns = 'w'
    
    def __init__(self, query):
        """
        Initialize a Filter node with a query and dialect attribute.
        
        Args:
            query: The filter query string
        """
        # Call parent constructor with Attribute and query
        super().__init__(
            Attribute(Dialect="http://schemas.microsoft.com/wbem/wsman/1/WQL"),
            query
        )


# Note: The package structure is handled by module imports.
# xmlns is a class attribute.