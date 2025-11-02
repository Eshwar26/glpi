# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node

class Reason(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::Reason
    WSMan Reason node handling.
    """
    xmlns = 's'
    
    @staticmethod
    def support():
        return {
            'Text': "s:Text",
        }
    
    def text(self):
        """
        Get the text content from the Reason node.
        
        Returns:
            str: The text string, or empty string if not found
        """
        text_node = self.get('Text')
        
        if text_node:
            return text_node.string()
        
        return ''


# Note: The package structure is handled by module imports.
# xmlns is a class attribute.