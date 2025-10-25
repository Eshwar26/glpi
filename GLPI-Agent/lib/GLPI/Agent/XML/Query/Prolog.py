"""
GLPI::Agent::XML::Query::Prolog - Prolog agent message

Initial message sent by the agent to the server before any task is
processed, requiring execution parameters.
"""

from typing import Any

from ..Query import Query


class Prolog(Query):
    def __init__(self, **params: Any) -> None:
        if not params.get('deviceid'):
            raise ValueError("no deviceid parameter for Prolog XML query")

        super().__init__(query='PROLOG', token='12345678', **params)


