# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node

class EndOfSequence(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::EndOfSequence
    WSMan EndOfSequence node handling.
    """
    xmlns = 'w'


# Note: The package structure is handled by module imports.
# xmlns is a class attribute.