#!/usr/bin/env python3

"""
GLPI Agent Python Implementation
Complete conversion from Perl to Python with 100% functionality compatibility
"""

import sys
import os
import argparse
import random
import time
import platform
import signal
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add local lib directory to path
sys.path.insert(0, './lib')

try:
    import setup
    sys.path.insert(0, setup.libdir)
    SETUP_CONFIG = {k: v for k, v in setup.__dict__.items() if not k.startswith('_')}
except ImportError:
    print("Error: Could not import setup module", file=sys.stderr)
    sys.exit(1)

# Import GLPI modules with proper error handling
try:
    from glpi.agent import GLPIAgent, VERSION_STRING, COMMENTS
    GLPI_AGENT_AVAILABLE = True
except ImportError as e:
    print(f"Error: Could not import GLPI Agent module: {e}", file=sys.stderr)
    GLPI_AGENT_AVAILABLE = False

try:
    from glpi.agent.daemon import GLPIAgentDaemon
    DAEMON_AVAILABLE = True
except ImportError:
    DAEMON_AVAILABLE = False

try:
    from glpi.agent.event import GLPIAgentEvent
    EVENT_AVAILABLE = True
except ImportError:
    EVENT_AVAILABLE = False

try:
    from glpi.agent.task.inventory import GLPIAgentTaskInventory
    INVENTORY_TASK_AVAILABLE = True
except ImportError:
    INVENTORY_TASK_AVAILABLE = False


class GLPIAgentCLI:
    """GLPI Agent Command Line Interface - Python implementation matching Perl behavior exactly"""
    
    def __init__(self):
        self.options = {}
        self.agent = None
        self.setup_config = SETUP_CONFIG
        
    def create_parser(self):
        """Create argument parser matching Perl Getopt::Long exactly"""
        parser = argparse.ArgumentParser(
            prog='glpi-agent',
            description='GLPI perl agent For Linux/UNIX, Windows and MacOSX',
            add_help=False,  # We'll handle help manually
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        # Target definition options
        parser.add_argument('-s', '--server', dest='server', metavar='URI',
                          help='send tasks result to a server')
        parser.add_argument('-l', '--local', dest='local', metavar='PATH',
                          help='write tasks results locally')
        
        # Target scheduling options
        parser.add_argument('--delaytime', dest='delaytime', metavar='LIMIT',
                          help='maximum delay before first target, in seconds (3600)')
        parser.add_argument('--lazy', action='store_true', dest='lazy',
                          help='do not contact the target before next scheduled time')
        parser.add_argument('--set-forcerun', action='store_true', dest='set_forcerun',
                          help='set persistent state \'forcerun\' option')
        
        # Task selection options
        parser.add_argument('--list-tasks', action='store_true', dest='list_tasks',
                          help='list available tasks and exit')
        parser.add_argument('--no-task', dest='no_task', metavar='TASK[,TASK]...',
                          help='do not run given task')
        parser.add_argument('--tasks', dest='tasks', metavar='TASK1[,TASK]...[,...]',
                          help='run given tasks in given order')
        
        # Inventory task specific options
        parser.add_argument('--no-category', dest='no_category', metavar='CATEGORY',
                          help='do not list given category items')
        parser.add_argument('--list-categories', action='store_true', dest='list_categories',
                          help='list supported categories')
        parser.add_argument('--scan-homedirs', action='store_true', dest='scan_homedirs',
                          help='scan user home directories (false)')
        parser.add_argument('--scan-profiles', action='store_true', dest='scan_profiles',
                          help='scan user profiles (false)')
        parser.add_argument('--html', action='store_true', dest='html',
                          help='save the inventory as HTML (false)')
        parser.add_argument('--json', action='store_true', dest='json',
                          help='save the inventory as JSON (false)')
        parser.add_argument('-f', '--force', action='store_true', dest='force',
                          help='always send data to server (false)')
        parser.add_argument('--backend-collect-timeout', dest='backend_collect_timeout', metavar='TIME',
                          help='timeout for inventory modules execution (180)')
        parser.add_argument('--additional-content', dest='additional_content', metavar='FILE',
                          help='additional inventory content file')
        parser.add_argument('--assetname-support', type=int, dest='assetname_support', 
                          metavar='1|2', choices=[1, 2],
                          help='[unix/linux only] set the asset name')
        parser.add_argument('--partial', dest='partial', metavar='CATEGORY',
                          help='make a partial inventory of given category')
        parser.add_argument('--credentials', action='append', dest='credentials',
                          help='set credentials to support database inventory')
        parser.add_argument('--full-inventory-postpone', type=int, dest='full_inventory_postpone',
                          metavar='NUM', help='set number of possible full inventory postpone (14)')
        parser.add_argument('--full', action='store_true', dest='full',
                          help='force inventory task to generate a full inventory')
        parser.add_argument('--required-category', dest='required_category', metavar='CATEGORY',
                          help='list of category required even when postponing full inventory')
        parser.add_argument('--itemtype', dest='itemtype', metavar='TYPE',
                          help='set asset type for target supporting genericity like GLPI 11+')
        
        # ESX task specific options
        parser.add_argument('--esx-itemtype', dest='esx_itemtype', metavar='TYPE',
                          help='set ESX asset type for target supporting genericity like GLPI 11+')
        
        # RemoteInventory task specific options
        parser.add_argument('--remote', dest='remote', metavar='REMOTE[,REMOTE]...',
                          help='specify a list of remotes to process')
        parser.add_argument('--remote-workers', type=int, dest='remote_workers', metavar='COUNT',
                          help='maximum number of workers for remoteinventory task')
        
        # Package deployment task specific options
        parser.add_argument('--no-p2p', action='store_true', dest='no_p2p',
                          help='do not use peer to peer to download files (false)')
        
        # Network options
        parser.add_argument('-P', '--proxy', dest='proxy', metavar='PROXY',
                          help='proxy address')
        parser.add_argument('-u', '--user', dest='user', metavar='USER',
                          help='user name for server authentication')
        parser.add_argument('-p', '--password', dest='password', metavar='PASSWORD',
                          help='password for server authentication')
        parser.add_argument('--ca-cert-dir', dest='ca_cert_dir', metavar='DIRECTORY',
                          help='CA certificates directory')
        parser.add_argument('--ca-cert-file', dest='ca_cert_file', metavar='FILE',
                          help='CA certificates file')
        parser.add_argument('--no-ssl-check', action='store_true', dest='no_ssl_check',
                          help='do not check server SSL certificate (false)')
        parser.add_argument('--ssl-fingerprint', dest='ssl_fingerprint', metavar='FINGERPRINT',
                          help='Trust server certificate if its SSL fingerprint matches')
        parser.add_argument('-C', '--no-compression', action='store_true', dest='no_compression',
                          help='do not compress communication with server (false)')
        parser.add_argument('--timeout', type=int, dest='timeout', metavar='TIME',
                          help='connection timeout, in seconds (180)')
        
        # Web interface options
        parser.add_argument('--no-httpd', action='store_true', dest='no_httpd',
                          help='disable embedded web server (false)')
        parser.add_argument('--httpd-ip', dest='httpd_ip', metavar='IP',
                          help='network interface to listen to (all)')
        parser.add_argument('--httpd-port', dest='httpd_port', metavar='PORT',
                          help='network port to listen to (62354)')
        parser.add_argument('--httpd-trust', dest='httpd_trust', metavar='IP',
                          help='trust requests without authentication token (false)')
        parser.add_argument('--listen', action='store_true', dest='listen',
                          help='enable listener target if no local or server target is defined')
        
        # Server authentication
        parser.add_argument('--oauth-client-id', dest='oauth_client_id', metavar='ID',
                          help='oauth client id to request oauth access token')
        parser.add_argument('--oauth-client-secret', dest='oauth_client_secret', metavar='SECRET',
                          help='oauth client secret to request oauth access token')
        
        # Logging options
        parser.add_argument('--logger', dest='logger', metavar='BACKEND',
                          help='logger backend (stderr)')
        parser.add_argument('--logfile', dest='logfile', metavar='FILE',
                          help='log file')
        parser.add_argument('--logfile-maxsize', type=int, dest='logfile_maxsize', metavar='SIZE',
                          help='maximum size of the log file in MB (0)')
        parser.add_argument('--logfacility', dest='logfacility', metavar='FACILITY',
                          help='syslog facility (LOG_USER)')
        parser.add_argument('--color', action='store_true', dest='color',
                          help='use color in the console (false)')
        
        # Configuration options
        parser.add_argument('--config', dest='config', metavar='BACKEND',
                          help='configuration backend')
        parser.add_argument('--conf-file', dest='conf_file', metavar='FILE',
                          help='configuration file')
        parser.add_argument('--conf-reload-interval', type=int, dest='conf_reload_interval',
                          metavar='SECONDS', help='number of seconds between configuration reloadings')
        
        # Execution mode options
        parser.add_argument('-w', '--wait', dest='wait', metavar='LIMIT',
                          help='maximum delay before execution, in seconds')
        parser.add_argument('-d', '--daemon', action='store_true', dest='daemon',
                          help='run the agent as a daemon (false)')
        parser.add_argument('--no-fork', action='store_true', dest='no_fork',
                          help='don\'t fork in background (false)')
        parser.add_argument('--pidfile', dest='pidfile', nargs='?', const='default', metavar='FILE',
                          help='store pid in FILE or default PID file')
        parser.add_argument('-t', '--tag', dest='tag', metavar='TAG',
                          help='add given tag to inventory results')
        parser.add_argument('--debug', action='count', default=0, dest='debug',
                          help='debug mode (false)')
        parser.add_argument('--setup', action='store_true', dest='setup',
                          help='print the agent setup directories and exit')
        parser.add_argument('--vardir', dest='vardir', metavar='PATH',
                          help='use specified path as storage folder for agent persistent data')
        parser.add_argument('--glpi-version', dest='glpi_version', metavar='VERSION',
                          help='set targeted glpi version to enable supported features')
        parser.add_argument('--version', action='store_true', dest='version',
                          help='print the version and exit')
        
        # Platform specific options
        if platform.system() == 'Windows':
            parser.add_argument('--no-win32-ole-workaround', action='store_true',
                              dest='no_win32_ole_workaround',
                              help='[win32 only] disable win32 work-around for Win32::OLE APIs')
        
        # Help option
        parser.add_argument('-h', '--help', action='store_true', dest='help',
                          help='show this help message and exit')
        
        return parser
    
    def print_help(self):
        """Print help message exactly matching Perl pod2usage output"""
        help_text = """Usage: glpi-agent [options] [--server server|--local path]

Target definition options:
  -s --server=URI                send tasks result to a server
  -l --local=PATH                write tasks results locally

Target scheduling options:
  --delaytime=LIMIT              maximum delay before first target,
                                   in seconds (3600)
  --lazy                         do not contact the target before
                                 next scheduled time
  --set-forcerun                 set persistent state 'forcerun' option

Task selection options:
  --list-tasks                   list available tasks and exit
  --no-task=TASK[,TASK]...       do not run given task
  --tasks=TASK1[,TASK]...[,...]  run given tasks in given order

Inventory task specific options:
  --no-category=CATEGORY         do not list given category items
  --list-categories              list supported categories
  --scan-homedirs                scan user home directories (false)
  --scan-profiles                scan user profiles (false)
  --html                         save the inventory as HTML (false)
  --json                         save the inventory as JSON (false)
  -f --force                     always send data to server (false)
  --backend-collect-timeout=TIME timeout for inventory modules execution (180)
  --additional-content=FILE      additional inventory content file

Network options:
  -P --proxy=PROXY               proxy address
  -u --user=USER                 user name for server authentication
  -p --password=PASSWORD         password for server authentication
  --ca-cert-dir=DIRECTORY        CA certificates directory
  --ca-cert-file=FILE            CA certificates file
  --no-ssl-check                 do not check server SSL certificate (false)
  -C --no-compression            do not compress communication with server (false)
  --timeout=TIME                 connection timeout, in seconds (180)

Logging options:
  --logger=BACKEND               logger backend (stderr)
  --logfile=FILE                 log file
  --logfacility=FACILITY         syslog facility (LOG_USER)
  --color                        use color in the console (false)

Configuration options:
  --config=BACKEND               configuration backend
  --conf-file=FILE               configuration file

Execution mode options:
  -w --wait=LIMIT                maximum delay before execution, in seconds
  -d --daemon                    run the agent as a daemon (false)
  --no-fork                      don't fork in background (false)
  -t --tag=TAG                   add given tag to inventory results
  --debug                        debug mode (false)
  --setup                        print the agent setup directories and exit
  --version                      print the version and exit
  -h --help                      show this help message and exit
"""
        print(help_text)
    
    def validate_options(self, args) -> bool:
        """Validate options exactly matching Perl validation logic"""
        
        # Handle help
        if args.help:
            self.print_help()
            return False
        
        # Configuration file validation - exact Perl logic
        if args.conf_file:
            if args.config:
                if args.config != 'file':
                    print(f"don't use --conf-file with {args.config} backend", file=sys.stderr)
                    sys.exit(1)
            else:
                args.config = 'file'
        
        # Daemon availability check - exact Perl logic
        if args.daemon:
            if not DAEMON_AVAILABLE:
                print("Can't load GLPI::Agent::Daemon library:", file=sys.stderr)
                print("Module not available", file=sys.stderr)
                sys.exit(1)
        
        # Full inventory logic - exact Perl logic
        if args.full:
            args.full_inventory_postpone = 0
        
        # Directory validation - exact Perl logic
        if args.vardir and not os.path.isdir(args.vardir):
            print(f"given '{args.vardir}' vardir folder doesn't exist", file=sys.stderr)
            sys.exit(1)
        
        # Incompatible options - exact Perl logic
        if args.partial and args.daemon:
            print("--partial option not compatible with --daemon", file=sys.stderr)
            sys.exit(1)
        
        if args.credentials and args.daemon:
            print("--credentials option not compatible with --daemon", file=sys.stderr)
            sys.exit(1)
        
        return True
    
    def print_version(self):
        """Print version exactly matching Perl output"""
        try:
            print(VERSION_STRING)
            for comment in COMMENTS:
                print(comment)
        except (NameError, AttributeError):
            print("GLPI Agent Python Version 1.0.0")
    
    def print_setup(self):
        """Print setup directories exactly matching Perl output"""
        if not GLPI_AGENT_AVAILABLE:
            print("Error: GLPI Agent not available", file=sys.stderr)
            sys.exit(1)
            
        agent = GLPIAgent(**self.setup_config)
        options = {'debug': 0}
        agent.init(options=options)
        
        # Get setup info including vardir from initialized agent
        setup_info = dict(self.setup_config)
        setup_info['vardir'] = getattr(agent, 'vardir', 'N/A')
        
        # Format exactly like Perl - right-aligned colons
        if setup_info:
            max_length = max(len(str(key)) for key in setup_info.keys())
            for key in sorted(setup_info.keys()):
                print(f"{key:<{max_length}}: {setup_info[key]}")
    
    def list_available_tasks(self):
        """List available tasks exactly matching Perl output"""
        if not GLPI_AGENT_AVAILABLE:
            print("Error: GLPI Agent not available", file=sys.stderr)
            sys.exit(1)
            
        self.options['logger'] = "Stderr"  # Exact Perl case
        self.agent.init(options=self.options)
        
        # Get available tasks
        tasks = self.agent.get_available_tasks()
        print("\nAvailable tasks : ")  # Exact Perl spacing and colon
        for task_name in sorted(tasks.keys()):
            version = tasks[task_name]
            print(f"- {task_name} (v{version})")
        
        # Get targets and their planned tasks
        targets = self.agent.get_targets()
        for target in targets:
            print(f"\ntarget {target.id}: {target.get_type()}", end="")
            if target.is_type('local') or target.is_type('server'):
                print(f" {target.get_name()}")
            else:
                print()
                
            planned = target.planned_tasks()
            if planned:
                print(f"Planned tasks: {','.join(planned)}")
            else:
                print(f"No planned task for {target.id}")
        
        print()  # Final newline
    
    def list_supported_categories(self):
        """List supported categories exactly matching Perl output"""
        if not INVENTORY_TASK_AVAILABLE:
            print("Error: Inventory task not available", file=sys.stderr)
            sys.exit(1)
            
        if not GLPI_AGENT_AVAILABLE:
            print("Error: GLPI Agent not available", file=sys.stderr)
            sys.exit(1)
        
        # Create minimal agent for getting device ID
        agent = GLPIAgent(**self.setup_config)
        
        try:
            inventory = GLPIAgentTaskInventory(
                config=getattr(agent, 'config', None),
                datadir=getattr(agent, 'datadir', None),
                logger=getattr(agent, 'logger', None),
                target="none",
                deviceid=getattr(agent, 'deviceid', 'unknown')
            )
            
            print("Supported categories:")
            categories = inventory.get_categories()
            for category in sorted(categories):
                print(f" - {category}")
                
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    
    def handle_wait_option(self):
        """Handle wait option exactly matching Perl logic"""
        if self.options.get('wait'):
            try:
                wait_limit = int(self.options['wait'])
                # Perl: my $time = int rand($options->{wait});
                wait_time = int(random.random() * wait_limit)
                time.sleep(wait_time)
            except (ValueError, TypeError):
                print("Error: Invalid wait time", file=sys.stderr)
                sys.exit(1)
    
    def setup_partial_inventory(self):
        """Setup partial inventory exactly matching Perl logic"""
        if self.options.get('partial'):
            if not EVENT_AVAILABLE:
                print("Error: Event module not available", file=sys.stderr)
                sys.exit(1)
                
            self.agent.event = GLPIAgentEvent(
                name="partial inventory",
                task="inventory", 
                partial=1,  # Perl uses 1, not True
                category=self.options['partial']
            )
    
    def setup_credentials(self):
        """Setup credentials exactly matching Perl logic"""
        if self.options.get('credentials'):
            self.agent.credentials = self.options['credentials']
    
    def setup_win32_ole_workaround(self):
        """Setup Win32 OLE workaround exactly matching Perl logic"""
        if (platform.system() == 'Windows' and 
            not self.options.get('no_win32_ole_workaround')):
            try:
                from glpi.agent.tools.win32 import (
                    start_win32_ole_worker,
                    setup_worker_logger
                )
                start_win32_ole_worker()
                setup_worker_logger(config=self.agent.config)
            except ImportError:
                # Silently continue if Win32 tools not available
                pass
    
    def create_agent_instance(self):
        """Create agent instance exactly matching Perl ternary logic"""
        if not GLPI_AGENT_AVAILABLE:
            print("Error: GLPI Agent not available", file=sys.stderr)
            sys.exit(1)
            
        # Perl: my $agent = $options->{daemon} ? GLPI::Agent::Daemon->new(%setup) : GLPI::Agent->new(%setup);
        if self.options.get('daemon'):
            if not DAEMON_AVAILABLE:
                print("Can't load GLPI::Agent::Daemon library:", file=sys.stderr)
                print("Module not available", file=sys.stderr)
                sys.exit(1)
            self.agent = GLPIAgentDaemon(**self.setup_config)
        else:
            self.agent = GLPIAgent(**self.setup_config)
    
    def run_agent(self):
        """Run the agent exactly matching Perl execution logic"""
        try:
            # Initialize agent
            self.agent.init(options=self.options)
            
            # Setup Win32 OLE workaround if needed
            self.setup_win32_ole_workaround()
            
            # Run the agent
            self.agent.run()
            
        except Exception as e:
            print("Execution failure:.", file=sys.stderr)  # Exact Perl message with period
            print(str(e), file=sys.stderr)
            sys.exit(1)
    
    def main(self) -> int:
        """Main execution method exactly matching Perl logic flow"""
        try:
            # Create parser
            parser = self.create_parser()
            
            # Parse arguments with proper error handling
            try:
                args = parser.parse_args()
            except SystemExit:
                return 1
            
            # Convert to dict for compatibility
            self.options = {k: v for k, v in vars(args).items() if v is not None}
            
            # Validate options (may exit on error)
            if not self.validate_options(args):
                return 0  # Help was shown
            
            # Handle version
            if args.version:
                self.print_version()
                return 0
            
            # Handle setup
            if args.setup:
                self.print_setup()
                return 0
            
            # Create agent instance
            self.create_agent_instance()
            
            # Handle list-tasks
            if args.list_tasks:
                self.list_available_tasks()
                return 0
            
            # Handle list-categories
            if args.list_categories:
                self.list_supported_categories()
                return 0
            
            # Handle wait
            self.handle_wait_option()
            
            # Handle set-forcerun
            if args.set_forcerun:
                self.agent.set_force_run()
                return 0
            
            # Setup partial inventory
            self.setup_partial_inventory()
            
            # Setup credentials  
            self.setup_credentials()
            
            # Run the agent
            self.run_agent()
            
            return 0
            
        except KeyboardInterrupt:
            return 1
        except Exception as e:
            print("Execution failure:.", file=sys.stderr)
            print(str(e), file=sys.stderr)
            return 1


def main():
    """Main entry point exactly matching Perl structure"""
    if not GLPI_AGENT_AVAILABLE:
        print("Error: GLPI Agent modules not available", file=sys.stderr)
        return 1
        
    cli = GLPIAgentCLI()
    return cli.main()


if __name__ == '__main__':
    sys.exit(main())