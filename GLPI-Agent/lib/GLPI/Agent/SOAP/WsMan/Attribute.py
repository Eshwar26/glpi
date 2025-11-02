from typing import Any, Dict, List, Optional


class Attribute:
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::Attribute
    WSMan Attribute handling.
    """

    def __init__(self, **params: Any):
        self._params = params

    def get(self, key: Optional[str] = None) -> Any:
        if key:
            return self._params.get(key)
        attributes = []
        for k, v in self._params.items():
            attributes.extend([f"-{k}", v])
        return attributes

    @classmethod
    def must_understand(cls, value: Optional[bool] = None) -> 'Attribute':
        return cls(s_mustUnderstand=value if value is not None else "true")