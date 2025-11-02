# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node
# from glpi.agent.soap.wsman.attribute import Attribute

class SequenceId(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::SequenceId
    WSMan SequenceId node handling.
    """
    xmlns = 'p'

    def __init__(self):
        """
        Initialize a SequenceId node with must_understand('false') and index = 1.
        """
        # Call the parent (Node) constructor just like Perl's SUPER::new(...)
        super().__init__(Attribute.must_understand("false"), 1)

        # Perl: $self->{_index} = 1;
        self._index = 1

    def index(self):
        """
        Get the current index value.

        Returns:
            int: The internal index value.
        """
        return self._index