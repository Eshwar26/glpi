# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node

class ExitCode(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::ExitCode
    WSMan ExitCode node handling.
    """
    xmlns = 'rsp'


# Note: The package structure is handled by module imports.
# xmlns is a class attribute.