# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node
# from glpi.agent.soap.wsman.max_elements import MaxElements

class Pull(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::Pull
    WSMan Pull node handling.
    """
    xmlns = 'n'
    
    def __init__(self, *params):
        """
        Initialize a Pull node with optional parameters.
        
        Args:
            *params: Variable arguments to pass to parent constructor
        """
        # Call parent constructor with all parameters
        super().__init__(*params)
        
        # Check if MaxElements is already in params
        has_max_elements = any(type(p).__name__ == 'MaxElements' for p in params)
        
        # If no MaxElements provided, add default one for pull operations
        if not has_max_elements:
            self.push(MaxElements(32000, for_pull=True))


# Note: The package structure is handled by module imports.
# xmlns is a class attribute.