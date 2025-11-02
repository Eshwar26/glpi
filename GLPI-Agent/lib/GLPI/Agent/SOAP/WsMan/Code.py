# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node


class Code(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::Code
    WSMan Code node handling.
    """

    @staticmethod
    def support():
        return {
            'Value': 's:Value',
        }

    def xmlns(self):
        return 'rsp' if hasattr(self, '_signal') and self._signal else 's'

    @classmethod
    def signal(cls, signal: str):
        code_map = {
            'terminate': "http://schemas.microsoft.com/wbem/wsman/1/windows/shell/signal/terminate",
        }
        if signal not in code_map:
            return None
        new_instance = cls(code_map[signal])
        new_instance._signal = True
        return new_instance

    def __init__(self, code: str):
        super().__init__(code)