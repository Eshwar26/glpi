# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node

class ReferenceParameters(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::ReferenceParameters
    WSMan ReferenceParameters node handling.
    """
    xmlns = 'a'
    
    @staticmethod
    def support():
        return {
            'ResourceURI': "w:ResourceURI",
            'SelectorSet': "w:SelectorSet",
        }


# Note: The package structure is handled by module imports.
# xmlns is a class attribute.