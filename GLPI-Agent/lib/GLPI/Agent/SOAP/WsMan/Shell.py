
import re

class Shell(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::Shell
    Handles WSMan Shell node operations.
    """
    xmlns = 'rsp'
    xsd = "http://schemas.microsoft.com/wbem/wsman/1/windows/shell"

    @classmethod
    def support(cls):
        """
        Returns supported WSMan selectors.

        Returns:
            dict: Supported element mappings.
        """
        return {
            'Selector': 'w:Selector',
        }

    def __init__(self, *params):
        """
        Initialize a Shell node.

        Args:
            *params: Optional parameters for initialization (like Perl @params).
        """
        # Perl:
        # if $params[0] is a HASH ref and contains 'rsp:ResourceUri', fix case
        if params and isinstance(params[0], dict):
            if 'rsp:ResourceUri' in params[0]:
                params[0]['rsp:ResourceURI'] = params[0].pop('rsp:ResourceUri')

        # Call the parent Node constructor
        super().__init__(*params)

        # Perl: add attributes if no parameters are passed
        if not params:
            self.push(
                Attribute(f"xmlns:{self.xmlns}", self.xsd),
                InputStreams(),
                OutputStreams()
            )

    def commandline(self, command):
        """
        Create and return a CommandLine node from a shell command string.

        Args:
            command (str): The command string to parse.

        Returns:
            CommandLine: A CommandLine node with Command and optional Arguments.
        """
        # Perl regex: my ($cmd, $args) = $command =~ /^\s*(\S+)\s*(.*)$/;
        match = re.match(r"^\s*(\S+)\s*(.*)$", command)
        if not match:
            return None
        cmd, args = match.groups()

        # Create CommandLine -> Command
        cmdline = CommandLine(
            Attribute(self.namespace()),
            Command(cmd)
        )

        # Add Arguments if present
        if args and len(args.strip()) > 0:
            cmdline.push(Arguments(args))

        return cmdline