# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.enumerate_response import EnumerateResponse

class PullResponse(EnumerateResponse):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::PullResponse
    WSMan PullResponse node handling.
    """
    
    @staticmethod
    def support():
        return {
            'EnumerationContext': "n:EnumerationContext",
            'Items': "n:Items",
            'EndOfSequence': "n:EndOfSequence",
        }


# Note: The package structure is handled by module imports.
# This class inherits from EnumerateResponse instead of Node.