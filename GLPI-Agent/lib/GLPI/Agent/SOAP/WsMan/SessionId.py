# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node
# from glpi.agent.soap.wsman.attribute import Attribute
import uuid
import re

class SessionId(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::SessionId
    WSMan SessionId node handling.
    """
    xmlns = 'p'

    def __init__(self, sessionid=None):
        """
        Initialize a SessionId node.
        If sessionid is provided, use it directly.
        Otherwise, generate a UUID-based session ID.
        
        Args:
            sessionid (str, optional): Predefined session ID. Defaults to None.
        """
        if sessionid:
            # Perl: return $class->SUPER::new($sessionid) if $sessionid;
            super().__init__(sessionid)
            self._uuid = None
        else:
            # Perl: my $uuid = Data::UUID->new()->create_str();
            new_uuid = str(uuid.uuid4())

            # Perl: $class->SUPER::new(Attribute->must_understand("false"), "uuid:$uuid")
            super().__init__(Attribute.must_understand("false"), f"uuid:{new_uuid}")

            # Perl: $self->{_uuid} = $uuid;
            self._uuid = new_uuid

    def uuid(self):
        """
        Get the UUID string from the SessionId.
        
        Returns:
            str or None: The UUID part of the session identifier.
        """
        # Perl equivalent:
        # my ($uuid) = $self->string =~ /^uuid:(.*)$/;
        if hasattr(self, "string") and callable(getattr(self, "string")):
            match = re.match(r"^uuid:(.*)$", self.string())
            uuid_from_string = match.group(1) if match else None
        else:
            uuid_from_string = None

        # Perl logic:
        # return unless $self->{_uuid} || $uuid;
        if not self._uuid and not uuid_from_string:
            return None

        # return $self->{_uuid} if $self->{_uuid};
        if self._uuid:
            return self._uuid

        # return $self->{_uuid} = $uuid;
        self._uuid = uuid_from_string
        return self._uuid