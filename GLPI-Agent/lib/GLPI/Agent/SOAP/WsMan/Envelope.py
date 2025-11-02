# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node
# from glpi.agent.soap.wsman.attribute import Attribute
# from glpi.agent.soap.wsman.header import Header
# from glpi.agent.soap.wsman.body import Body

class Envelope(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::Envelope
    WSMan Envelope node handling.
    """
    xmlns = 's'
    
    # Namespace mappings
    _ns = {
        's': "http://www.w3.org/2003/05/soap-envelope",
        'a': "http://schemas.xmlsoap.org/ws/2004/08/addressing",
        'n': "http://schemas.xmlsoap.org/ws/2004/09/enumeration",
        'w': "http://schemas.dmtf.org/wbem/wsman/1/wsman.xsd",
        'p': "http://schemas.microsoft.com/wbem/wsman/1/wsman.xsd",
        'b': "http://schemas.dmtf.org/wbem/wsman/1/cimbinding.xsd",
        'wsmid': "http://schemas.dmtf.org/wbem/wsman/identity/1/wsmanidentity.xsd"
    }
    
    @staticmethod
    def support():
        return {
            'Body': "s:Body",
            'Header': "s:Header",
        }
    
    def __init__(self, *nodes):
        """
        Initialize an Envelope node with optional child nodes.
        
        Args:
            *nodes: Variable arguments for child nodes
        """
        # Convert nodes to list for manipulation
        nodes_list = list(nodes)
        
        # Handle special case where first argument is a dict with 's:Envelope' key
        if nodes_list and isinstance(nodes_list[0], dict) and 's:Envelope' in nodes_list[0]:
            nodes_list = [nodes_list[0]['s:Envelope']]
        
        # Call parent constructor with processed nodes
        super().__init__(*nodes_list)
    
    def body(self):
        """
        Get the Body node from the envelope.
        
        Returns:
            Body: The body node, or a new one if not found
        """
        body_node = self.get('Body')
        
        return body_node if body_node else Body()
    
    def header(self):
        """
        Get the Header node from the envelope.
        
        Returns:
            Header: The header node, or a new one if not found
        """
        header_node = self.get('Header')
        
        return header_node if header_node else Header()
    
    def reset_namespace(self, namespaces):
        """
        Reset namespace attributes on the envelope.
        
        Args:
            namespaces: Either an Attribute object or a comma-separated string of namespace prefixes
        """
        attributes = []
        
        # Check if namespaces is a string (not an Attribute object)
        if isinstance(namespaces, str):
            ns_list = namespaces.split(',')
            for ns in ns_list:
                ns = ns.strip()  # Remove any whitespace
                if ns in self._ns:
                    attributes.append(f"xmlns:{ns}")
                    attributes.append(self._ns[ns])
            
            # Call parent's reset_namespace with new Attribute
            super().reset_namespace(Attribute(*attributes))
        else:
            # Assume it's an Attribute object
            super().reset_namespace(namespaces)


# Note: The package structure is handled by module imports.
# xmlns is a class attribute.