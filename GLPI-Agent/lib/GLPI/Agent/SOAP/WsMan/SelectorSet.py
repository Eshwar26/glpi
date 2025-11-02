# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node
# from glpi.agent.soap.wsman.selector import Selector

class SelectorSet(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::SelectorSet
    WSMan SelectorSet node handling.
    """
    xmlns = 'w'

    @classmethod
    def support(cls):
        """
        Returns supported WSMan SelectorSet mappings.

        Returns:
            dict: Mapping of supported selector elements.
        """
        return {
            'Selector': 'w:Selector',
        }