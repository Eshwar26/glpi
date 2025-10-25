"""
GLPI Agent Version Module

This module has the only purpose to simplify the way the agent is released. This
file could be automatically generated and overridden during packaging.

It permits to re-define agent VERSION and agent PROVIDER during packaging so
any distributor can simplify his distribution process and permit to identify
clearly the origin of the agent.

It also permits to put build comments in COMMENTS. Each list element will
be reported in output while using --version option. This will be also seen in logs.
The idea is to authorize the provider to put useful information needed while
agent issue is reported.
One very useful information should be first defined like in that example:

COMMENTS = [
    "Based on GLPI Agent 1.16-dev"
]
"""

VERSION = "1.16-dev"
PROVIDER = "GLPI"
COMMENTS = []

__all__ = ['VERSION', 'PROVIDER', 'COMMENTS']