#!/usr/bin/env python3
"""
GLPI Agent Config - Python Implementation

This module handles configuration management for the GLPI Agent,
supporting file-based and registry-based configuration backends.
"""

import os
import sys
import glob
import warnings
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

# Optional target imports
try:
    from .target.local_target import LocalTarget
except ImportError:
    LocalTarget = None

try:
    from .target.server_target import ServerTarget
except ImportError:
    ServerTarget = None

try:
    from .target.listener_target import ListenerTarget
except ImportError:
    ListenerTarget = None


DEFAULT = {
    'additional-content': None,
    'backend-collect-timeout': 180,
    'ca-cert-dir': None,
    'ca-cert-file': None,
    'color': None,
    'conf-reload-interval': 0,
    'debug': None,
    'delaytime': 3600,
    'esx-itemtype': None,
    'glpi-version': None,
    'itemtype': None,
    'remote-scheduling': 0,
    'remote-workers': 1,
    'force': None,
    'html': None,
    'json': None,
    'lazy': None,
    'local': None,
    'logger': 'Stderr',
    'logfile': None,
    'logfacility': 'LOG_USER',
    'logfile-maxsize': None,
    'no-category': [],
    'no-httpd': None,
    'no-ssl-check': None,
    'no-compression': None,
    'no-task': [],
    'no-p2p': None,
    'oauth-client-id': None,
    'oauth-client-secret': None,
    'password': None,
    'proxy': None,
    'httpd-ip': None,
    'httpd-port': 62354,
    'httpd-trust': [],
    'listen': None,
    'remote': None,
    'scan-homedirs': None,
    'scan-profiles': None,
    'server': None,
    'ssl-cert-file': None,
    'ssl-fingerprint': None,
    'ssl-keystore': None,
    'tag': None,
    'tasks': None,
    'timeout': 180,
    'user': None,
    'vardir': None,
    'assetname-support': 1,
    'full-inventory-postpone': 14,
    'required-category': [],
    'snmp-retries': 0,
}

CONF_RELOAD_INTERVAL_MIN = 60


def empty(val: Any) -> bool:
    """
    Check if a value is considered empty.
    
    Args:
        val: Value to check
        
    Returns:
        True if value is None, empty string, or empty collection
    """
    if val is None:
        return True
    if isinstance(val, str) and val.strip() == "":
        return True
    if isinstance(val, (list, dict)) and len(val) == 0:
        return True
    return False


class Config:
    """
    Configuration manager for GLPI Agent.
    
    Handles loading configuration from files, registry (Windows),
    and command-line options.
    """
    
    def __init__(self, **params: Any):
        """
        Initialize configuration.
        
        Args:
            **params: Configuration parameters including:
                - defaults: Default configuration dict
                - options: Command-line options dict
                - vardir: Variable directory path
                
        Raises:
            TypeError: If defaults is not a dictionary
        """
        defaults = params.get('defaults')
        if defaults is not None and not isinstance(defaults, dict):
            raise TypeError("config: default can only be a dict")

        options = params.get('options', {})
        vardir = params.get('vardir')

        self._confdir: Optional[str] = None
        self._options: Dict[str, Any] = options
        self._default: Dict[str, Any] = defaults or DEFAULT.copy()

        # Determine config directory from conf-file if provided
        conf_file = options.get('conf-file')
        if conf_file and Path(conf_file).exists() and self._confdir is None:
            self._confdir = str(Path(conf_file).parent.resolve())

        # Load configuration
        self._loadDefaults()

        # Fix relative paths in confdir (matches ./ or ../ or .../ etc)
        if self._confdir and re.match(r'^\.+/', self._confdir):
            self._confdir = str(Path(self._confdir).resolve())

        self._loadFromBackend(options.get('conf-file'), options.get('config'))
        self._loadUserParams(options)

        # Handle vardir special case
        if 'vardir' in self._default:
            vardir_option = options.get('vardir')
            if vardir_option and Path(vardir_option).is_dir():
                self.__dict__['vardir'] = vardir_option
            elif ('vardir' not in self.__dict__ or 
                  ('vardir' in self.__dict__ and 
                   not Path(self.__dict__['vardir']).is_dir())):
                self.__dict__['vardir'] = vardir
            self._options['vardir'] = self.__dict__.get('vardir')

        self._checkContent()

    def __getattr__(self, name: str) -> Any:
        """
        Allow attribute-style access to config values.
        
        Args:
            name: Attribute name
            
        Returns:
            Configuration value
            
        Raises:
            AttributeError: If attribute doesn't exist
        """
        # Avoid recursion for private attributes
        if name.startswith('_'):
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            )
        return self.__dict__.get(name)

    def __setattr__(self, name: str, value: Any) -> None:
        """Allow setting attributes normally."""
        self.__dict__[name] = value

    def reload(self) -> None:
        """Reload configuration from sources."""
        self._loadDefaults()
        self._loadFromBackend(
            self.__dict__.get('conf-file'),
            self.__dict__.get('config')
        )
        self._loadUserParams(self._options)
        self._checkContent()
        self.__dict__['delaytime'] = 0

    def _loadFromBackend(self, conf_file: Optional[str], 
                        config: Optional[str]) -> None:
        """
        Load configuration from appropriate backend.
        
        Args:
            conf_file: Configuration file path
            config: Backend type ('file', 'registry', 'none')
            
        Raises:
            RuntimeError: If backend is unavailable or unknown
        """
        if conf_file:
            backend = 'file'
        elif config:
            backend = config
        elif sys.platform.startswith('win'):
            backend = 'registry'
        else:
            backend = 'file'

        if backend == 'registry':
            if not sys.platform.startswith('win'):
                raise RuntimeError("Config: Unavailable configuration backend")
            self._loadFromRegistry()
        elif backend == 'file':
            self.loadedConfs: Dict[str, int] = {}
            if conf_file:  # Only load if file is specified
                self.loadFromFile({'file': conf_file})
            # Clean up temporary tracking dict
            if hasattr(self, 'loadedConfs'):
                del self.loadedConfs
        elif backend == 'none':
            pass
        else:
            raise RuntimeError(
                f"Config: Unknown configuration backend '{backend}'"
            )

    def _loadDefaults(self) -> None:
        """Load default configuration values."""
        for key, value in self._default.items():
            self.__dict__[key] = value

        # Try to find config directory if not set
        if self._confdir and Path(self._confdir).is_dir():
            return

        for candidate in ['./etc', '../etc', '../../etc']:
            p = Path(candidate)
            if p.exists() and p.is_dir():
                self._confdir = str(p.resolve())
                break
        
        if self._confdir:
            self._confdir = str(Path(self._confdir).resolve())

    def _loadFromRegistry(self) -> None:
        """Load configuration from Windows registry."""
        warnings.warn("Registry backend is not implemented in this port.")

    def confdir(self) -> Optional[str]:
        """Get configuration directory path."""
        return self._confdir

    def loadFromFile(self, params: Optional[Dict[str, str]]) -> None:
        """
        Load configuration from file.
        
        Args:
            params: Dictionary with 'file' key containing path
            
        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If file isn't readable
            RuntimeError: If no configuration file specified
        """
        if params and params.get('file'):
            file = params['file']
        else:
            file = f"{self._confdir}/agent.cfg" if self._confdir else None

        if not file:
            raise RuntimeError("Config: no configuration file")

        if not Path(file).is_file():
            raise FileNotFoundError(f"Config: non-existing file {file}")
        
        if not os.access(file, os.R_OK):
            raise PermissionError(f"Config: non-readable file {file}")

        # Check if already loaded
        if (hasattr(self, 'loadedConfs') and 
            self.loadedConfs.get(file)):
            logger_val = self.__dict__.get('logger', '')
            if str(logger_val).capitalize() == 'Stderr':
                warnings.warn(f"Config: {file} configuration file still loaded")
            return

        # Mark as loaded
        if hasattr(self, 'loadedConfs'):
            self.loadedConfs[file] = 1

        try:
            with open(file, 'r', encoding='utf-8') as handle:
                for line in handle:
                    line = line.rstrip('\n')
                    
                    # Match: key = value
                    m = re.match(r'^\s*([\w-]+)\s*=\s*(.*)$', line)
                    if m:
                        key = m.group(1)
                        val = m.group(2).rstrip()
                        
                        # Remove quotes if present
                        n = re.match(r"^(['\"])(.*?)\1$", val)
                        if n:
                            val = n.group(2)
                        else:
                            # Remove trailing comments
                            val = re.sub(r'\s*#.+$', '', val).rstrip()
                        
                        if key in self._default:
                            self.__dict__[key] = val
                        elif key.lower() == 'include':
                            self._includeDirective(val, file)
                        else:
                            warnings.warn(
                                f"Config: unknown configuration directive {key}"
                            )
                    else:
                        # Match: include directive
                        inc = re.match(r'^\s*include\s+(.+)$', line, re.I)
                        if inc:
                            include = inc.group(1)
                            
                            # Remove quotes if present
                            n = re.match(r"^(['\"])(.*?)\1$", include)
                            if n:
                                include = n.group(2)
                            else:
                                # Remove trailing comments
                                include = re.sub(r'\s*#.+$', '', include).rstrip()
                            
                            self._includeDirective(include, file)
                            
        except Exception as e:
            warnings.warn(f"Config: Failed to open {file}: {e}")

    def _includeDirective(self, include: str, currentconfig: str) -> None:
        """
        Handle include directive in config file.
        
        Args:
            include: Path to include (file or directory)
            currentconfig: Path of current config file
        """
        include_path = Path(include)
        
        # Make relative paths absolute
        if not include_path.is_absolute():
            include_path = Path(currentconfig).parent / include

        try:
            include_path = include_path.resolve()
        except Exception:
            return

        if not include_path.exists():
            return

        if include_path.is_dir():
            # Include all .cfg files in directory
            for cfg in sorted(glob.glob(str(include_path) + "/*.cfg")):
                if Path(cfg).is_file() and os.access(cfg, os.R_OK):
                    self.loadFromFile({'file': cfg})
        elif include_path.is_file() and os.access(include_path, os.R_OK):
            self.loadFromFile({'file': str(include_path)})

    def _loadUserParams(self, params: Dict[str, Any]) -> None:
        """
        Load user-provided parameters.
        
        Args:
            params: User parameters dictionary
        """
        for key, value in params.items():
            self.__dict__[key] = value

    def _checkContent(self) -> None:
        """
        Validate and normalize configuration content.
        
        Raises:
            RuntimeError: If configuration is invalid
        """
        # Add File logger if logfile is set
        if self.__dict__.get('logfile'):
            logger_val = self.__dict__.get('logger', '')
            if 'File' not in logger_val:
                self.__dict__['logger'] = f"{logger_val},File" if logger_val else "File"

        # Check for conflicting SSL cert options
        if (self.__dict__.get('ca-cert-file') and 
            self.__dict__.get('ca-cert-dir')):
            raise RuntimeError(
                "Config: use either 'ca-cert-file' or 'ca-cert-dir' option, not both"
            )

        # Check for file logger without logfile
        logger_val = self.__dict__.get('logger')
        logfile_val = self.__dict__.get('logfile')
        if (not empty(logger_val) and 
            re.search(r'file', logger_val, re.I) and 
            empty(logfile_val)):
            raise RuntimeError(
                "Config: usage of 'file' logger backend makes 'logfile' option mandatory"
            )

        # Convert comma-separated strings to lists
        multi_options = [
            'logger', 'local', 'server', 'httpd-trust', 'no-task', 
            'no-category', 'required-category', 'tasks', 'ssl-fingerprint'
        ]
        for option in multi_options:
            if option in self.__dict__:
                value = self.__dict__[option]
                if isinstance(value, str):
                    # Split on one or more commas
                    self.__dict__[option] = [
                        v.strip() for v in re.split(r',+', value) if v.strip()
                    ]
                elif isinstance(value, list):
                    self.__dict__[option] = value
                else:
                    self.__dict__[option] = []

        # Resolve paths to absolute paths
        path_options = [
            'ca-cert-file', 'ca-cert-dir', 'ssl-cert-file', 
            'logfile', 'vardir'
        ]
        for option in path_options:
            if option in self.__dict__:
                val = self.__dict__[option]
                if not empty(val):
                    self.__dict__[option] = str(Path(val).resolve())

        # Validate conf-reload-interval
        cri = self.__dict__.get('conf-reload-interval')
        if cri is not None and cri != 0:
            try:
                cri = int(cri)
                if cri < 0:
                    cri = 0
                elif 0 < cri < CONF_RELOAD_INTERVAL_MIN:
                    cri = CONF_RELOAD_INTERVAL_MIN
                self.__dict__['conf-reload-interval'] = cri
            except (ValueError, TypeError):
                self.__dict__['conf-reload-interval'] = CONF_RELOAD_INTERVAL_MIN

    def hasFilledParam(self, paramName: str) -> bool:
        """
        Check if parameter exists and is a non-empty list.
        
        Args:
            paramName: Parameter name to check
            
        Returns:
            True if parameter is a non-empty list
        """
        if paramName not in self.__dict__:
            return False
        value = self.__dict__[paramName]
        return isinstance(value, list) and len(value) > 0

    def logger(self) -> Dict[str, Any]:
        """
        Get logger configuration.
        
        Returns:
            Dictionary of logger configuration values
        """
        return {
            k: self.__dict__.get(k)
            for k in ['debug', 'logger', 'logfacility', 'logfile', 
                     'logfile-maxsize', 'color']
        }

    def getTargets(self, **params: Any) -> List[Any]:
        """
        Get configured targets.
        
        Args:
            **params: Parameters including:
                - logger: Logger instance
                - vardir: Variable directory path
                
        Returns:
            List of target objects
            
        Raises:
            RuntimeError: If target loading fails
        """
        logger = params.get('logger')
        vardir = params.get('vardir')
        targets = []
        
        # Local targets
        if 'local' in self.__dict__ and self.__dict__['local']:
            if LocalTarget is None:
                warnings.warn("LocalTarget not available")
            else:
                LocalTarget.reset()
                for path in self.__dict__['local']:
                    target = LocalTarget(
                        logger=logger,
                        maxDelay=self.__dict__['delaytime'],
                        delaytime=min(self.__dict__['delaytime'], 3600),
                        basevardir=vardir,
                        path=path,
                        html=self.__dict__.get('html'),
                        json=self.__dict__.get('json'),
                        glpi=self.__dict__.get('glpi-version'),
                    )
                    targets.append(target)

        # Server targets
        if 'server' in self.__dict__ and self.__dict__['server']:
            if ServerTarget is None:
                warnings.warn("ServerTarget not available")
            else:
                ServerTarget.reset()
                for url in self.__dict__['server']:
                    target = ServerTarget(
                        logger=logger,
                        delaytime=self.__dict__['delaytime'],
                        basevardir=vardir,
                        url=url,
                        tag=self.__dict__.get('tag'),
                        glpi=self.__dict__.get('glpi-version'),
                    )
                    targets.append(target)

        # Listener target
        if ('listen' in self.__dict__ and self.__dict__['listen'] and 
            not targets and not self.__dict__.get('no-httpd')):
            if ListenerTarget is None:
                raise RuntimeError(
                    "Config: ListenerTarget not available"
                )
            try:
                target = ListenerTarget(
                    logger=logger,
                    delaytime=self.__dict__['delaytime'],
                    basevardir=vardir,
                    glpi=self.__dict__.get('glpi-version'),
                )
                targets.append(target)
            except Exception as e:
                raise RuntimeError(
                    f"Config: Failure while loading ListenerTarget: {e}"
                )

        return targets


if __name__ == "__main__":
    # Test the config
    config = Config(options={
        'debug': '1',
        'server': 'https://glpi.example.com/front/inventory.php',
        'local': '/tmp/glpi'
    })
    print("Config directory:", config.confdir())
    print("Logger config:", config.logger())
    print("Has filled 'local':", config.hasFilledParam('local'))