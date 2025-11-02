# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node
# from glpi.agent.soap.wsman.attribute import Attribute
import re

class Selector(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::Selector
    WSMan Selector node handling.
    """
    xmlns = 'w'

    def __init__(self, *condition):
        """
        Initialize a Selector node.

        Args:
            *condition: Either (Attribute, value) pairs, or a single string like 'Name=Value'.
        """
        # Perl logic: if only one argument and it matches key=value, split it.
        if len(condition) == 1 and isinstance(condition[0], str):
            match = re.match(r"^(\w+)=(\w+)$", condition[0])
            if match:
                name, value = match.groups()
                # Convert to Attribute("Name"=name), value
                condition = (Attribute(name="Name", value=name), value)

        # Call Node constructor with unpacked arguments
        super().__init__(*condition)