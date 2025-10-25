#!/usr/bin/env python3
"""
GLPI Agent Logger - Python Implementation

This module provides logging functionality for the GLPI Agent.
Supports multiple backends and verbosity levels.
"""

import sys
import importlib
from typing import Optional, List, Callable, Dict, Any, Protocol

# Log level constants
LOG_DEBUG2 = 5
LOG_DEBUG = 4
LOG_INFO = 3
LOG_WARNING = 2
LOG_ERROR = 1
LOG_NONE = 0

# Package-level shared logger config
_config: Optional[Dict[str, Any]] = None


class LoggerBackend(Protocol):
    """Protocol defining the interface for logger backends."""
    
    def addMessage(self, *, level: str, message: str) -> None:
        """Add a message to the log."""
        ...
    
    def reload(self) -> None:
        """Reload backend configuration."""
        ...
    
    @property
    def test(self) -> bool:
        """Indicate if this is a test backend."""
        ...


class StderrBackend:
    """Default stderr logging backend."""
    
    def __init__(self, **kwargs):
        pass

    def addMessage(self, *, level: str, message: str) -> None:
        """Write message to stderr with level prefix."""
        print(f"[{level.upper()}] {message}", file=sys.stderr)

    def reload(self) -> None:
        """No-op for stderr backend."""
        pass

    @property
    def test(self) -> bool:
        """This is not a test backend."""
        return False


class Logger:
    """
    Main logger class for GLPI Agent.
    
    Supports multiple backends, verbosity levels, and event callbacks.
    """
    
    def __init__(self, **params: Any) -> None:
        """
        Initialize logger with configuration.
        
        Args:
            **params: Configuration parameters including:
                - config: Configuration object or dict
                - debug: Debug level (0-2)
                - logger: List of backend names
                - prefix: Message prefix string
        """
        global _config

        first_pass = _config is None

        # Initialize or reset Logger configuration
        if "config" in params:
            cfg = params["config"]
            if hasattr(cfg, "logger"):
                _config = cfg.logger()
            else:
                _config = cfg if isinstance(cfg, dict) else {}
        elif first_pass:
            _config = params.copy()
        else:
            # Later new creation updates the shared config
            if _config is None:
                _config = {}
            for k, v in params.items():
                _config[k] = v

        # Determine verbosity level from debug setting
        debug = _config.get("debug", 0)

        if debug >= 2:
            verbosity = LOG_DEBUG2
        elif debug == 1:
            verbosity = LOG_DEBUG
        else:
            verbosity = LOG_INFO

        self.verbosity: int = verbosity
        self.prefix: Optional[str] = _config.get("prefix")
        self._event_cb: Optional[Callable] = None
        self.backends: List[Any] = []

        # Determine which backends to load
        backends_cfg = _config.get("logger") if _config else None
        if backends_cfg is None:
            backends_cfg = params.get("logger")
        
        backends_list = backends_cfg if backends_cfg else ["Stderr"]

        # Load backends (avoid duplicates)
        seen: Dict[str, bool] = {}
        for backend in backends_list:
            backend_name = backend.capitalize()
            if backend_name in seen:
                continue
            seen[backend_name] = True

            logger_backend = None

            if backend_name == "Stderr":
                logger_backend = StderrBackend(**(_config or {}))
            else:
                # Try to load custom backend module
                package_name = f"glpi_agent.logger.{backend_name.lower()}"
                try:
                    module = importlib.import_module(package_name)
                    
                    # Try different backend instantiation methods
                    if hasattr(module, "LoggerBackend"):
                        logger_backend = module.LoggerBackend(**(_config or {}))
                    elif hasattr(module, backend_name):
                        backend_class = getattr(module, backend_name)
                        logger_backend = backend_class(**(_config or {}))
                    elif hasattr(module, "new"):
                        logger_backend = module.new(**(_config or {}))
                    else:
                        print(
                            f"Backend {backend_name} has no valid constructor",
                            file=sys.stderr
                        )
                        
                except ImportError as e:
                    print(
                        f"Failed to load Logger backend {backend_name}: {e}",
                        file=sys.stderr
                    )
                    continue
                except Exception as e:
                    print(
                        f"Error initializing Logger backend {backend_name}: {e}",
                        file=sys.stderr
                    )
                    continue

            if logger_backend:
                self.backends.append(logger_backend)
                if first_pass and not getattr(logger_backend, "test", False):
                    self.debug(f"Logger backend {backend_name} initialized")

        # Log version string if available
        if first_pass:
            glpi_agent = sys.modules.get("glpi_agent")
            if glpi_agent and hasattr(glpi_agent, "VERSION_STRING"):
                self.debug(glpi_agent.VERSION_STRING)

    def _log(self, *, level: str = "info", message: str, skip_log: bool = False) -> None:
        """
        Internal logging method.
        
        Args:
            level: Log level (debug2, debug, info, warning, error)
            message: Message to log
            skip_log: Skip logging to backends (for event callbacks only)
        """
        if not message:
            return

        # Add prefix if configured
        if self.prefix:
            message = f"{self.prefix}{message}"

        # Remove trailing newlines
        message = message.rstrip("\n")

        # Call event callback if registered
        if callable(self._event_cb):
            self._event_cb(level=level, message=message)
            if skip_log:
                return

        # Send to all backends
        for backend in self.backends:
            if hasattr(backend, "addMessage"):
                backend.addMessage(level=level, message=message)

    def register_event_cb(self, callback: Callable[[str, str], None]) -> None:
        """
        Register a callback for log events.
        
        Args:
            callback: Function to call with level and message
        """
        self._event_cb = callback

    def reload(self) -> None:
        """Reload all backend configurations."""
        for backend in self.backends:
            if hasattr(backend, "reload"):
                backend.reload()

    def debug_level(self) -> int:
        """
        Get current debug level.
        
        Returns:
            Debug level (0, 1, or 2)
        """
        if callable(self._event_cb):
            return LOG_DEBUG2 - LOG_INFO
        return self.verbosity - LOG_INFO if self.verbosity > LOG_INFO else 0

    def debug2(self, message: str) -> None:
        """
        Log debug2 level message (most verbose).
        
        Args:
            message: Message to log
        """
        if self.verbosity >= LOG_DEBUG2 or callable(self._event_cb):
            self._log(
                level="debug2",
                message=message,
                skip_log=self.verbosity < LOG_DEBUG2
            )

    def debug(self, message: str) -> None:
        """
        Log debug level message.
        
        Args:
            message: Message to log
        """
        if self.verbosity >= LOG_DEBUG or callable(self._event_cb):
            self._log(
                level="debug",
                message=message,
                skip_log=self.verbosity < LOG_DEBUG
            )

    def debug_result(self, **params: Any) -> None:
        """
        Log a debug result message.
        
        Args:
            **params: Parameters including:
                - status: Status string
                - data: Data object (determines success if status not provided)
                - action: Action description
        """
        if self.verbosity < LOG_DEBUG:
            return

        status = params.get("status")
        if not status:
            status = "success" if params.get("data") else "no result"
        
        action = params.get("action", "action")

        self._log(
            level="debug",
            message=f"- {action}: {status}"
        )

    def info(self, message: str) -> None:
        """
        Log info level message.
        
        Args:
            message: Message to log
        """
        if self.verbosity >= LOG_INFO:
            self._log(level="info", message=message)

    def warning(self, message: str) -> None:
        """
        Log warning level message.
        
        Args:
            message: Message to log
        """
        if self.verbosity >= LOG_WARNING:
            self._log(level="warning", message=message)

    def error(self, message: str) -> None:
        """
        Log error level message.
        
        Args:
            message: Message to log
        """
        if self.verbosity >= LOG_ERROR:
            self._log(level="error", message=message)


# Convenience function for creating logger
def create_logger(**kwargs: Any) -> Logger:
    """
    Create a new logger instance.
    
    Args:
        **kwargs: Configuration parameters
        
    Returns:
        Logger instance
    """
    return Logger(**kwargs)


if __name__ == "__main__":
    # Basic test
    logger = Logger(debug=2)
    logger.debug2("This is a debug2 message")
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    logger.debug_result(action="test operation", status="completed")