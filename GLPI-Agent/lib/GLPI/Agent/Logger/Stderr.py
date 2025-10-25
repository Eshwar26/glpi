"""
GLPI::Agent::Logger::Stderr - A stderr backend for the logger

This is a stderr-based backend for the logger. It supports coloring based on
message level on Unix platforms.
"""

import sys

from GLPI.Agent.Logger.Backend import Backend


class Stderr(Backend):
    """Stderr-based logger backend with optional color support."""
    
    def __init__(self, color=False, **params):
        """
        Initialize the stderr logger backend.
        
        Args:
            color (bool): Whether to use colored output
            **params: Additional parameters passed to parent
        """
        super().__init__(params.get('config'))
        
        # ANSI color formats for different log levels
        self._formats = None
        if color:
            self._formats = {
                'warning': '\033[1;35m[{}] {}\033[0m\n',  # Magenta
                'error': '\033[1;31m[{}] {}\033[0m\n',    # Red
                'info': '\033[1;34m[{}]\033[0m {}\n',     # Blue
                'debug': '\033[1;1m[{}]\033[0m {}\n',     # Bold
                'debug2': '\033[1;36m[{}]\033[0m {}\n'    # Cyan
            }
    
    def add_message(self, level, message):
        """
        Add a message to stderr.
        
        Args:
            level (str): Log level (debug, info, warning, error)
            message (str): Log message
        """
        if not message:
            return
        
        level = level or 'info'
        
        # Get the appropriate format
        if self._formats and level in self._formats:
            format_str = self._formats[level]
        else:
            format_str = '[{}] {}\n'
        
        # Write to stderr
        sys.stderr.write(format_str.format(level, message))
        sys.stderr.flush()
