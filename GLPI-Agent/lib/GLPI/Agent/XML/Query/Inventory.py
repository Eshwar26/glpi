"""
GLPI XML Query Inventory - Python Implementation

Inventory message wrapper for OCS XML protocol format.
"""

from typing import Any

from ..Query import Query


class Inventory(Query):
    """Inventory XML query message."""

    def __init__(self, **params: Any) -> None:
        if 'content' not in params:
            raise ValueError("no content parameter for XML query")

        super().__init__(query='INVENTORY', **params)


