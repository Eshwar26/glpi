#!/usr/bin/env python3
"""Getopt - Command-line option parsing for installer"""

import sys
import re
from typing import Dict, Optional, Any


# Define all available options
_OPTIONS = [
    'backend-collect-timeout=i',
    'ca-cert-file=s',
    'clean',
    'color',
    'cron=i',
    'debug|d=i',
    'delaytime=i',
    'distro=s',
    'no-question|Q',
    'esx-itemtype=s',
    'extract=s',
    'force',
    'full-inventory-postpone=i',
    'glpi-version=s',
    'help|h',
    'install',
    'itemtype=s',
    'list',
    'local|l=s',
    'logger=s',
    'logfacility=s',
    'logfile=s',
    'no-httpd',
    'no-ssl-check',
    'no-category=s',
    'no-compression|C',
    'no-task=s',
    'no-p2p',
    'password|p=s',
    'proxy|P=s',
    'httpd-ip=s',
    'httpd-port=s',
    'httpd-trust=s',
    'reinstall',
    'remote=s',
    'remote-workers=i',
    'required-category=s',
    'runnow',
    'scan-homedirs',
    'scan-profiles',
    'server|s=s',
    'service=i',
    'silent|S',
    'skip=s',
    'snap',
    'ssl-fingerprint=s',
    'tag|t=s',
    'tasks=s',
    'type=s',
    'uninstall',
    'unpack',
    'user|u=s',
    'use-current-user-proxy',
    'verbose|v',
    'version',
]


def _parse_option_spec(opt_spec: str) -> tuple:
    """
    Parse option specification.
    
    Args:
        opt_spec: Option specification string (e.g., "server|s=s", "clean", "debug|d=i")
        
    Returns:
        Tuple of (plus_flag, is_string, is_int, long_name, short_name)
    """
    plus = opt_spec.endswith('+')
    if plus:
        opt_spec = opt_spec[:-1]
    
    is_string = opt_spec.endswith('=s')
    if is_string:
        opt_spec = opt_spec[:-2]
    
    is_int = opt_spec.endswith('=i')
    if is_int:
        opt_spec = opt_spec[:-2]
    
    # Parse long|short format
    match = re.match(r'^([^|]+)(?:\|(.))?$', opt_spec)
    if match:
        long_name = match.group(1)
        short_name = match.group(2)
    else:
        long_name = opt_spec
        short_name = None
    
    return (plus, is_string, is_int, long_name, short_name)


# Build options lookup table
_OPTIONS_MAP: Dict[str, tuple] = {}
for opt in _OPTIONS:
    plus, is_string, is_int, long_name, short_name = _parse_option_spec(opt)
    _OPTIONS_MAP[f"--{long_name}"] = (plus, is_string, is_int, long_name)
    if short_name:
        _OPTIONS_MAP[f"-{short_name}"] = (plus, is_string, is_int, long_name)


def GetOptions() -> Optional[Dict[str, Any]]:
    """
    Parse command-line options.
    
    Returns:
        Dictionary of parsed options, or None on error
    """
    options: Dict[str, Any] = {}
    args = sys.argv[1:]
    
    i = 0
    pending_long = None
    
    while i < len(args):
        arg = args[i]
        
        # Match option format: -option[=value] or --option[=value]
        match = re.match(r'^(-[^=]*)=?(.+)?$', arg)
        if match:
            opt_key = match.group(1)
            value = match.group(2) if match.group(2) else None
            
            if opt_key not in _OPTIONS_MAP:
                return None
            
            plus, is_string, is_int, long_name = _OPTIONS_MAP[opt_key]
            
            if plus:
                # Increment option
                options[long_name] = options.get(long_name, 0) + 1
                pending_long = None
            elif value and is_int:
                # Integer value provided with =
                options[long_name] = int(value)
                pending_long = None
            elif is_string and value:
                # String value provided with =
                options[long_name] = value
                pending_long = None
            elif is_string or is_int:
                # Option requires value, expect it in next arg
                pending_long = (long_name, is_int, is_string)
            else:
                # Boolean flag
                options[long_name] = 1
                pending_long = None
        elif pending_long:
            # Process pending option value
            long_name, is_int, is_string = pending_long
            if is_int:
                options[long_name] = int(arg)
            elif is_string:
                # Append if already exists (for multi-value strings)
                if long_name in options:
                    options[long_name] += " " + arg
                else:
                    options[long_name] = arg
            pending_long = None
        else:
            # Invalid argument
            return None
        
        i += 1
    
    return options


def Help() -> str:
    """Get help text"""
    return """glpi-agent-linux-installer [options]

  Target definition options:
    -s --server=URI                configure agent GLPI server
    -l --local=PATH                configure local path to store inventories

  Target scheduling options:
    --delaytime=LIMIT              maximum delay before target tasks first run, in seconds (3600)
                                   It also defines the maximum delay on network error.

  Task selection options:
    --no-task=TASK[,TASK]...       configure task to not run
    --tasks=TASK1[,TASK]...[,...]  configure tasks to run in a given order

  Inventory task specific options:
    --no-category=CATEGORY         configure category items to not inventory
    --scan-homedirs                set to scan user home directories (false)
    --scan-profiles                set to scan user profiles (false)
    --backend-collect-timeout=TIME set timeout for inventory modules execution (30)
    -t --tag=TAG                   configure tag to define in inventories
    --full-inventory-postpone=NUM  set number of possible full inventory postpone (14)
    --required-category=CATEGORY   list of category required even when postponing full inventory
    --itemtype=TYPE                set asset type for target supporting genericity like GLPI 11+

  ESX task specific options:
    --esx-itemtype=TYPE            set ESX asset type for target supporting genericity like GLPI 11+

  RemoteInventory specific options:
    --remote=REMOTE[,REMOTE]...    list of remotes for remoteinventory task
    --remote-workers=COUNT         maximum number of workers for remoteinventory task

  Package deployment task specific options:
    --no-p2p                       set to not use peer to peer to download
                                   deploy task packages

  Network options:
    -P --proxy=PROXY               proxy address
    --use-current-user-proxy       Configure proxy address from current user environment (false)
                                   and only if --proxy option is not used
    --ca-cert-file=FILE            CA certificates file
    --no-ssl-check                 do not check server SSL certificate (false)
    -C --no-compression            do not compress communication with server (false)
    --ssl-fingerprint=FINGERPRINT  Trust server certificate if its SSL fingerprint
                                   matches the given one
    -u --user=USER                 user name for server authentication
    -p --password=PASSWORD         password for server authentication

  Web interface options:
    --no-httpd                     disable embedded web server (false)
    --httpd-ip=IP                  set network interface to listen to (all)
    --httpd-port=PORT              set network port to listen to (62354)
    --httpd-trust=IP               list of IPs to trust (GLPI server only by default)

  Logging options:
    --logger=BACKEND               configure logger backend (stderr)
    --logfile=FILE                 configure log file path
    --logfacility=FACILITY         syslog facility (LOG_USER)
    --color                        use color in the console (false)
    --debug=DEBUG                  configure debug level (0)

  Execution mode options:
    --service                      setup the agent as service (true)
    --cron                         setup the agent as cron task running hourly (false)

  Other options:
    --glpi-version=<VERSION>       set targeted glpi version to enable supported features

  Installer options:
    --install                      install the agent (true)
    --uninstall                    uninstall the agent (false)
    --clean                        clean everything when uninstalling or before
                                   installing (false)
    --reinstall                    uninstall and then reinstall the agent (false)
    --list                         list embedded packages
    --extract=WHAT                 don't install but extract packages (nothing)
                                     - "nothing": still install but don't keep extracted packages
                                     - "keep": still install but keep extracted packages
                                     - "all": don't install but extract all packages
                                     - "rpm": don't install but extract all rpm packages
                                     - "deb": don't install but extract all deb packages
                                     - "snap": don't install but extract snap package
    --runnow                       run agent tasks on installation (false)
    --type=INSTALL_TYPE            select type of installation (typical)
                                     - "typical" to only install computer inventory and remote inventory tasks
                                     - "network" to install glpi-agent and network related tasks
                                     - "all" to install all tasks
                                     - or tasks to install in a comma-separated list
    -v --verbose                   make verbose install (false)
    --version                      print the installer version and exit
    -S --silent                    make installer silent (false)
    -Q --no-question               don't ask for configuration on prompt (false)
    --force                        try to force installation
    --distro                       force distro name when --force option is used
    --snap                         install snap package instead of using system packaging
    --skip=PKG_LIST                don't try to install listed packages
    -h --help                      print this help
"""

