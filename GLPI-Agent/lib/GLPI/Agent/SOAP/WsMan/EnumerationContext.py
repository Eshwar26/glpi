# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node

class EnumerationContext(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::EnumerationContext
    WSMan EnumerationContext node handling.
    """
    xmlns = 'n'
    xsd = "http://schemas.xmlsoap.org/ws/2004/09/enumeration"


# Note: The package structure is handled by module imports.
# xmlns and xsd are class attributes.