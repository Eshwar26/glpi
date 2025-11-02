# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node

class ReceiveResponse(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::ReceiveResponse
    WSMan ReceiveResponse node handling.
    """
    xmlns = 'rsp'
    
    @staticmethod
    def support():
        return {
            'Stream': "rsp:Stream",
            'CommandState': "rsp:CommandState",
        }


# Note: The package structure is handled by module imports.
# xmlns is a class attribute.