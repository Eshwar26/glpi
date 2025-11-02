# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node
# from glpi.agent.soap.wsman.enumeration_context import EnumerationContext
# from glpi.agent.soap.wsman.end_of_sequence import EndOfSequence

class EnumerateResponse(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::EnumerateResponse
    WSMan EnumerateResponse node handling.
    """
    xmlns = 'n'
    
    def __init__(self, *enum):
        """
        Initialize an EnumerateResponse node with optional enumeration items.
        
        Args:
            *enum: Variable arguments for enumeration items
        """
        # Call parent constructor with all parameters
        super().__init__(*enum)
        
        # If no parameters provided, add EndOfSequence
        if not enum:
            self.push(EndOfSequence())
    
    @staticmethod
    def support():
        return {
            'EnumerationContext': "n:EnumerationContext",
            'Items': "w:Items",
            'EndOfSequence': "w:EndOfSequence",
        }
    
    def items(self):
        """
        Extract and return all items from the response.
        
        Returns:
            list: List of dictionaries representing items
        """
        items = []
        for items_node in self.nodes("Items"):
            for item in items_node.nodes():
                items.extend(self._dump(item))
        
        return items
    
    def end_of_sequence(self):
        """
        Find and return the EndOfSequence node if present.
        
        Returns:
            EndOfSequence or None: The EndOfSequence node if found
        """
        for node in self.nodes():
            if type(node).__name__ == "EndOfSequence":
                return node
        return None
    
    def _dump(self, object_node):
        """
        Recursively dump node content to dictionary format.
        
        Args:
            object_node: The node to dump
            
        Returns:
            list: List of dictionaries representing the node data
        """
        dump_list = []
        dump_dict = {}
        
        for node in object_node.nodes():
            key = type(node).__name__
            nil = node.attribute('xsi:nil')
            nodes = node.nodes()
            
            if nil and nil == 'true':
                dump_dict[key] = None
            elif node.attribute('xsi:type'):
                dump_list.extend(self._dump(node))
                dump_dict = None
            elif type(node).__name__ and hasattr(node, 'dump_as_string') and node.dump_as_string():
                dump_dict[key] = node.string()
            else:
                if len(nodes) > 1:
                    dump_dict[key] = [n.string() for n in nodes]
                else:
                    dump_dict[key] = node.string()
        
        if dump_dict is not None:
            dump_list.append(dump_dict)
        
        return dump_list
    
    def context(self):
        """
        Get the EnumerationContext from the response.
        
        Returns:
            EnumerationContext: The context node, or a new one if not found
        """
        context_node = self.get('EnumerationContext')
        
        if context_node:
            context_node.set_namespace()
            return context_node
        
        return EnumerationContext()


# Note: The package structure is handled by module imports.
# xmlns is a class attribute.
# The BEGIN block's $INC manipulation is not needed in Python's import system.