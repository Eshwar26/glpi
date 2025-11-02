# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node

class To(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::To
    WSMan To node handling.
    """
    xmlns = 'a'
    xsd = "http://schemas.xmlsoap.org/ws/2004/08/addressing"
    
    @classmethod
    def anonymous(cls):
        """
        Create a To node with an anonymous address.
        
        Returns:
            To: A new To instance with the anonymous addressing role URI
        """
        return cls("http://schemas.xmlsoap.org/ws/2004/08/addressing/role/anonymous")


# Note: The package structure is handled by module imports.
# xmlns and xsd are class attributes.