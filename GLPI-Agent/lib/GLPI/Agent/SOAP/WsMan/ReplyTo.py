# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node
# from glpi.agent.soap.wsman.address import Address

class ReplyTo(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::ReplyTo
    WSMan ReplyTo node handling.
    """
    xmlns = 'a'
    
    @classmethod
    def anonymous(cls):
        """
        Create a ReplyTo node with an anonymous address.
        
        Returns:
            ReplyTo: A new ReplyTo instance with an anonymous Address
        """
        return cls(Address.anonymous())


# Note: The package structure is handled by module imports.
# xmlns is a class attribute.