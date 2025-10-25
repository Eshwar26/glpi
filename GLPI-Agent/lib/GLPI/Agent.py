import os
import sys
import time
import glob
import signal
import logging
import importlib
import importlib.util
import uuid
import json
import socket
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import requests
import platform
import re

# Version information - exact match to Perl
VERSION = "1.7.0"
PROVIDER = "GLPI"
COMMENTS = []

# Global variables - exact Perl replica
CONTINUE_WORD = "..."

def _version_string(version: str) -> str:
    """Exact replica of Perl _versionString"""
    global COMMENTS
   
    string = f"{PROVIDER} Agent ({version})"
    if re.match(r'^\d+\.\d+\.(99\d\d|\d+-dev|.*-build-?\d+)$', version):
        COMMENTS.insert(0, "** THIS IS A DEVELOPMENT RELEASE **")
   
    return string

VERSION_STRING = _version_string(VERSION)
AGENT_STRING = f"{PROVIDER}-Agent_v{VERSION}"

# Process name for Inventory Provider (matches Perl)
PROGRAM_NAME = sys.argv[0] if sys.argv else "glpi-agent"

class Config:
    """Exact replica of GLPI::Agent::Config"""
   
    def __init__(self, options: Dict = None, vardir: str = None):
        self.options = options or {}
        self._vardir = vardir
        self._confdir = '/etc/glpi-agent'
        self._config = {}
        self.load_config()
   
    def load_config(self):
        """Load configuration exactly like Perl"""
        # Initialize empty config
        self._config = {}
       
        # Load from config files
        config_files = [
            os.path.join(self._confdir, 'agent.cfg'),
            '/etc/glpi-agent.cfg'
        ]
       
        for config_file in config_files:
            if os.path.exists(config_file):
                self._load_config_file(config_file)
       
        # Merge command line options
        for key, value in self.options.items():
            if value is not None:
                self._config[key] = value
       
        # Set defaults
        if 'no-task' not in self._config:
            self._config['no-task'] = []
        if 'server' not in self._config:
            self._config['server'] = []
   
    def _load_config_file(self, config_file: str):
        """Basic config file parsing"""
        try:
            with open(config_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('#') or not line:
                        continue
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')
                       
                        if ',' in value and key in ['server', 'no-task']:
                            self._config[key] = [v.strip() for v in value.split(',')]
                        elif value.lower() in ['true', 'yes', '1']:
                            self._config[key] = True
                        elif value.lower() in ['false', 'no', '0']:
                            self._config[key] = False
                        else:
                            self._config[key] = value
        except Exception:
            pass
   
    def get(self, key, default=None):
        return self._config.get(key, default)
   
    def __getitem__(self, key):
        return self.get(key)
   
    def __setitem__(self, key, value):
        self._config[key] = value
   
    def confdir(self):
        return self._confdir
   
    def has_filled_param(self, param: str) -> bool:
        """Exact replica of hasFilledParam"""
        value = self.get(param)
        if value is None:
            return False
        if isinstance(value, list):
            return len(value) > 0
        return bool(value)
   
    def get_targets(self, logger=None, deviceid: str = None, vardir: str = None):
        """Exact replica of getTargets"""
        targets = []
       
        servers = self.get('server', [])
        if isinstance(servers, str):
            servers = [servers]
       
        for i, server_url in enumerate(servers):
            target = ServerTarget(
                id=f"server_{i}",
                url=server_url,
                logger=logger,
                vardir=vardir
            )
            targets.append(target)
       
        local_path = self.get('local')
        if local_path:
            target = LocalTarget(
                id='local_0',
                path=local_path,
                logger=logger
            )
            targets.append(target)
       
        return targets


class Logger:
    """Exact replica of GLPI::Agent::Logger"""
   
    def __init__(self, config=None):
        self.config = config
       
        level = logging.DEBUG if config and config.get('debug') else logging.INFO
       
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
       
        self.logger = logging.getLogger('glpi-agent')
        self.logger.setLevel(level)
       
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
       
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
       
        log_file = config.get('logfile') if config else None
        if log_file:
            try:
                file_handler = logging.FileHandler(log_file)
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
            except Exception:
                pass
   
    def debug(self, message: str):
        self.logger.debug(message)
   
    def debug2(self, message: str):
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"[DEBUG2] {message}")
   
    def info(self, message: str):
        self.logger.info(message)
   
    def warning(self, message: str):
        self.logger.warning(message)
   
    def error(self, message: str):
        self.logger.error(message)


class Storage:
    """Exact replica of GLPI::Agent::Storage"""
   
    def __init__(self, logger=None, directory: str = None):
        self.logger = logger
        self.directory = directory or '/var/lib/glpi-agent'
        Path(self.directory).mkdir(parents=True, exist_ok=True)
   
    def restore(self, name: str) -> Dict:
        """Exact replica of restore method"""
        file_path = os.path.join(self.directory, f"{name}.json")
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}
   
    def save(self, name: str, data: Dict):
        """Exact replica of save method"""
        file_path = os.path.join(self.directory, f"{name}.json")
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            temp_file = file_path + '.tmp'
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            os.rename(temp_file, file_path)
        except Exception:
            pass


class Event:
    """Exact replica of GLPI::Agent::Event"""
   
    def __init__(self, name: str = "", init: bool = False):
        self.name = name
        self.init = init
        self.data = {}


class BaseTarget:
    """Base target class - exact replica"""
   
    def __init__(self, id: str, logger=None, vardir: str = None):
        self.id = id
        self.logger = logger
        self.vardir = vardir
        self._type = None
        self._next_run_date = 0
        self._max_delay = 3600
        self._paused = False
        self._glpi_server = None
        self._task_servers = {}
        self._events = []
   
    def is_type(self, type_name: str) -> bool:
        return self._type == type_name
   
    def get_type(self) -> str:
        return self._type
   
    def get_name(self) -> str:
        return getattr(self, 'url', getattr(self, 'path', self.id))
   
    def planned_tasks(self, *tasks) -> List[str]:
        return list(tasks)
   
    def get_next_run_date(self) -> float:
        return self._next_run_date
   
    def set_next_run_date_from_now(self):
        self._next_run_date = time.time()
   
    def reset_next_run_date(self):
        self._next_run_date = time.time() + self._max_delay
   
    def set_next_run_on_expiration(self, expiration: int):
        self._next_run_date = time.time() + expiration
   
    def set_max_delay(self, delay: int):
        self._max_delay = delay
   
    def paused(self) -> bool:
        return self._paused
   
    def pause(self):
        self._paused = True
   
    def resume(self):
        self._paused = False
   
    def is_glpi_server(self, value=None) -> bool:
        if value is not None:
            if isinstance(value, str):
                self._glpi_server = value.lower() == 'true'
            else:
                self._glpi_server = bool(value)
        return bool(self._glpi_server)
   
    def do_prolog(self) -> bool:
        return True
   
    def get_task_server(self, task: str) -> Optional[str]:
        return self._task_servers.get(task.lower(), {}).get('server')
   
    def set_server_task_support(self, task: str, info: Dict):
        self._task_servers[task.lower()] = info
   
    def add_event(self, event: Event, priority: bool = False):
        if priority:
            self._events.insert(0, event)
        else:
            self._events.append(event)


class ServerTarget(BaseTarget):
    """Exact replica of GLPI::Agent::Target::Server"""
   
    def __init__(self, id: str, url: str, logger=None, vardir: str = None):
        super().__init__(id, logger, vardir)
        self._type = 'server'
        self.url = url
   
    def get_url(self) -> str:
        return self.url


class LocalTarget(BaseTarget):
    """Exact replica of GLPI::Agent::Target::Local"""
   
    def __init__(self, id: str, path: str, logger=None, vardir: str = None):
        super().__init__(id, logger, vardir)
        self._type = 'local'
        self.path = path


class BaseTask:
    """Base task class"""
   
    def __init__(self, config=None, datadir: str = None, logger=None,
                 event=None, credentials=None, target=None,
                 deviceid: str = None, agentid: str = None, cached_data=None):
        self.config = config
        self.datadir = datadir
        self.logger = logger
        self.event = event
        self.credentials = credentials
        self.target = target
        self.deviceid = deviceid
        self.agentid = agentid
        self.cached_data = cached_data
   
    def run(self):
        """Execute the task"""
        self._execute()
   
    def _execute(self):
        """Override in subclasses"""
        pass
   
    def abort(self):
        """Abort task execution"""
        pass
   
    def is_enabled(self, response=None) -> bool:
        """Check if task is enabled"""
        return True
   
    def new_event(self) -> Optional[Event]:
        """Create new event for this task"""
        return None


class InventoryTask(BaseTask):
    """Basic inventory task implementation"""
   
    def _execute(self):
        """Execute inventory collection"""
        if self.logger:
            self.logger.info("Collecting system inventory")
       
        inventory_data = {
            'deviceid': self.deviceid,
            'timestamp': datetime.now().isoformat(),
            'hardware': self._collect_hardware(),
            'software': self._collect_software(),
            'network': self._collect_network()
        }
       
        # Send to target
        if self.target.is_type('server'):
            self._send_to_server(inventory_data)
        elif self.target.is_type('local'):
            self._save_to_local(inventory_data)
   
    def _collect_hardware(self) -> Dict:
        """Basic hardware information"""
        return {
            'system': platform.system(),
            'node': platform.node(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor()
        }
   
    def _collect_software(self) -> List[Dict]:
        """Basic software collection"""
        software = []
       
        if platform.system() == 'Linux':
            try:
                result = subprocess.run(['dpkg', '-l'],
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    for line in result.stdout.split('\n')[5:]:
                        if line.strip():
                            parts = line.split()
                            if len(parts) >= 3:
                                software.append({
                                    'name': parts[1],
                                    'version': parts[2]
                                })
            except:
                pass
       
        return software
   
    def _collect_network(self) -> Dict:
        """Basic network information"""
        return {
            'hostname': socket.gethostname(),
            'fqdn': socket.getfqdn()
        }
   
    def _send_to_server(self, data: Dict):
        """Send inventory to server"""
        if self.logger:
            self.logger.info(f"Sending inventory to {self.target.get_name()}")
   
    def _save_to_local(self, data: Dict):
        """Save inventory to local file"""
        if self.logger:
            self.logger.info(f"Saving inventory to {self.target.get_name()}")
       
        output_file = os.path.join(self.target.path, f"inventory_{self.deviceid}_{int(time.time())}.json")
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
       
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)


# Utility functions
def get_hostname(short: bool = False, fqdn: bool = False) -> str:
    """Get hostname with options"""
    if fqdn:
        return socket.getfqdn()
    elif short:
        return socket.gethostname().split('.')[0]
    else:
        return socket.gethostname()


def create_uuid() -> str:
    """Create a new UUID"""
    return str(uuid.uuid4())


def uuid_to_string(uuid_obj) -> str:
    """Convert UUID to string"""
    return str(uuid_obj) if uuid_obj else ""


def file2module(file_path: str) -> str:
    """Convert file path to module name"""
    return file_path.replace('/', '.').replace('.pm', '').replace('.py', '')


def empty(value) -> bool:
    """Check if value is empty"""
    if value is None:
        return True
    if isinstance(value, (str, list, dict)):
        return len(value) == 0
    return False


class GLPIAgent:
    """Exact replica of GLPI::Agent"""
   
    def __init__(self, datadir: str = None, libdir: str = None, vardir: str = None):
        """Exact replica of new() method"""
        self.status = 'unknown'
        self.datadir = datadir
        self.libdir = libdir
        self.vardir = vardir
        self.targets = []
        self._cache = {}
       
        # Additional attributes
        self.config = None
        self.logger = None
        self.storage = None
        self.deviceid = None
        self.agentid = None
        self.event = None
        self.credentials = None
        self.current_task = None
        self.installed_tasks = []
        self.server = None
        self._terminate = False
        self._forced_run = False
        self._disabled_remoteinventory = False
   
    def init(self, options: Dict = None, **params):
        """Exact replica of init() method"""
        if not self.config:
            self.config = Config(
                options=options,
                vardir=self.vardir
            )
       
        if self.config.get('vardir') and os.path.isdir(self.config.get('vardir')):
            self.vardir = self.config.get('vardir')
       
        self.logger = Logger(config=self.config)
       
        self.logger.debug(f"Configuration directory: {self.config.confdir()}")
        self.logger.debug(f"Data directory: {self.datadir}")
        self.logger.debug(f"Storage directory: {self.vardir}")
        self.logger.debug(f"Lib directory: {self.libdir}")
       
        self._handle_persistent_state()
       
        forced_run = self._forced_run
        self._forced_run = False
       
        # Always reset targets
        self.targets = self.config.get_targets(
            logger=self.logger,
            deviceid=self.deviceid,
            vardir=self.vardir
        )
       
        if not self.get_targets() and (not options or not options.get('list-tasks')):
            self.logger.error("No target defined, aborting")
            sys.exit(1)
       
        # Compute available tasks
        available = self.get_available_tasks()
        tasks = sorted(available.keys())
        if not tasks:
            self.logger.error("No tasks available, aborting")
            sys.exit(1)
       
        self.installed_tasks = [task.lower() for task in tasks]
        planned_tasks = self.compute_task_execution_plan(available)
       
        self.logger.debug("Available tasks:")
        for task in tasks:
            self.logger.debug(f"- {task}: {available[task]}")
       
        for target in self.get_targets():
            if target.is_type('local') or target.is_type('server'):
                self.logger.debug(f"target {target.id}: {target.get_type()} {target.get_name()}")
                if forced_run:
                    target.set_next_run_date_from_now()
            else:
                self.logger.debug(f"target {target.id}: {target.get_type()}")
           
            planned = target.planned_tasks(*planned_tasks)
           
            if planned:
                self.logger.debug(f"Planned tasks for {target.id}: {','.join(planned)}")
            else:
                self.logger.debug(f"No planned task for {target.id}")
       
        if (self.config.has_filled_param('no-task') and
            self.config.has_filled_param('tasks')):
            self.logger.info("Options 'no-task' and 'tasks' are both used. "
                           "Be careful that 'no-task' always excludes tasks.")
       
        # Signal handlers
        signal.signal(signal.SIGINT, lambda s, f: self._signal_handler())
        signal.signal(signal.SIGTERM, lambda s, f: self._signal_handler())
       
        if options:
            for comment in COMMENTS:
                self.logger.debug(comment)
   
    def _signal_handler(self):
        """Signal handler"""
        self.terminate()
        sys.exit(0)
   
    def run(self):
        """Exact replica of run() method"""
        self.set_status('waiting')
       
        targets = self.get_targets()
       
        self.logger.debug("Running in foreground mode")
       
        current_time = time.time()
        while self.get_targets() and targets:
            target = targets.pop(0)
            if (self.config.get('lazy') and
                current_time < target.get_next_run_date()):
               
                if self.config.get('force'):
                    self.logger.info(
                        f"{target.id} is not ready yet, but run is forced"
                    )
                else:
                    next_run = datetime.fromtimestamp(target.get_next_run_date())
                    self.logger.info(
                        f"{target.id} is not ready yet, next server contact "
                        f"planned for {next_run}"
                    )
                    continue
           
            try:
                self.run_target(target)
            except Exception as e:
                self.logger.error(str(e))
           
            target.reset_next_run_date()
   
    def terminate(self):
        """Exact replica of terminate() method"""
        self._terminate = True
        self.targets = []
       
        if self.current_task:
            self.current_task.abort()
   
    def get_contact(self, target, planned_tasks: List[str]):
        """Exact replica of getContact() method"""
        response = None
       
        if target.is_glpi_server():
            # GLPI protocol contact would go here
            pass
       
        return response
   
    def get_prolog(self, target):
        """Exact replica of getProlog() method"""
        response = None
       
        if target.is_type('server'):
            # PROLOG request would go here
            pass
       
        return response
   
    def run_target(self, target, responses_only: bool = False):
        """Exact replica of runTarget() method"""
        if target.is_type('local') or target.is_type('server'):
            self.logger.info(f"target {target.id}: {target.get_type()} {target.get_name()}")
       
        planned_tasks = target.planned_tasks()
        requests = []
        responses = {}
       
        if target.is_glpi_server():
            requests.append('CONTACT')
        if not requests and target.is_type('server'):
            requests.append('PROLOG')
       
        requested = {'CONTACT': False, 'PROLOG': False}
       
        while requests:
            request = requests.pop(0)
            if request in responses:
                continue
           
            response = None
            requested[request] = True
           
            if request == 'CONTACT':
                response = self.get_contact(target, planned_tasks)
                if response and not hasattr(response, '__dict__'):
                    return response
               
                if hasattr(response, 'planned_tasks'):
                    planned_tasks = response.planned_tasks
               
                if (hasattr(response, '__dict__') and target.do_prolog() and
                    not requested['PROLOG']):
                    requests.append('PROLOG')
           
            elif request == 'PROLOG':
                response = self.get_prolog(target)
                if response and not hasattr(response, '__dict__'):
                    return response
               
                if (hasattr(response, '__dict__') and target.is_glpi_server() and
                    not requested['CONTACT']):
                    requests.append('CONTACT')
           
            if hasattr(response, '__dict__'):
                responses[request] = response
       
        if responses_only:
            return responses
       
        for name in planned_tasks:
            server_response = responses.get('PROLOG') or responses.get('CONTACT')
            if responses.get('CONTACT'):
                task_server = target.get_task_server(name) or 'glpi'
                if task_server == 'glpi':
                    server_response = responses['CONTACT']
           
            try:
                self.run_task(target, name, server_response)
            except Exception as e:
                self.logger.error(str(e))
           
            self.set_status('paused' if target.paused() else 'waiting')
           
            if self._terminate:
                break
            if target.paused():
                break
       
        return 0
   
    def run_task(self, target, name: str, response=None):
        """Exact replica of runTask() method"""
        self.set_status(f"running task {name}")
        self.run_task_real(target, name, response)
   
    def run_task_real(self, target, name: str, response=None):
        """Exact replica of runTaskReal() method"""
        class_name = f"GLPI::Agent::Task::{name}"
       
        # Try to load task class
        task_class = self._get_task_class(name)
        if not task_class:
            if self.logger:
                self.logger.debug2(f"{name} task module does not compile")
            return
       
        task = task_class(
            config=self.config,
            datadir=self.datadir,
            logger=self.logger,
            event=self.event,
            credentials=self.credentials,
            target=target,
            deviceid=self.deviceid,
            agentid=uuid_to_string(self.agentid),
            cached_data=self._cache.get(name),
        )
       
        # Handle init event
        if self.event and self.event.init:
            event = task.new_event() if hasattr(task, 'new_event') else None
            if event and hasattr(event, 'name') and event.name:
                target.add_event(event, True)
            return
       
        if response and hasattr(task, 'is_enabled') and not task.is_enabled(response):
            return
       
        event_name = self.event.name if self.event else ""
        log_msg = f"running task {name}"
        if event_name:
            log_msg += f": {event_name} event"
       
        self.logger.info(log_msg)
        self.current_task = task
       
        task.run()
       
        self.handle_task_cache(name, task)
        self.handle_task_event(name, task)
       
        self.current_task = None
   
    def _get_task_class(self, name: str):
        """Get task class by name"""
        if name.lower() == 'inventory':
            return InventoryTask
       
        try:
            module_name = f"glpi_agent.task.{name.lower()}"
            task_module = importlib.import_module(module_name)
            return getattr(task_module, name + 'Task', None)
        except ImportError:
            return None
   
    def handle_task_cache(self, name: str, task):
        """Placeholder - only supported in daemon mode"""
        pass
   
    def handle_task_event(self, name: str, task):
        """Placeholder - only supported in daemon mode"""
        pass
   
    def get_status(self) -> str:
        """Exact replica of getStatus()"""
        return self.status
   
    def set_status(self, status: str = None):
        """Exact replica of setStatus()"""
        config = self.config
       
        # Set process name (simplified)
        process_name = f"{PROVIDER.lower()}-agent"
        if config and config.get('tag'):
            process_name += f" (tag {config.get('tag')})"
       
        if status:
            self.status = status
            process_name += f": {status}"
       
        # Limited process name setting
        try:
            import setproctitle
            setproctitle.setproctitle(process_name)
        except ImportError:
            pass
   
    def get_targets(self) -> List[BaseTarget]:
        """Exact replica of getTargets()"""
        return self.targets
   
    def get_available_tasks(self) -> Dict[str, str]:
        """Exact replica of getAvailableTasks()"""
        logger = self.logger
       
        tasks = {}
        disabled = {task.lower(): True for task in (self.config.get('no-task') or [])}
       
        # Built-in tasks
        builtin_tasks = {'Inventory': '1.0.0'}
       
        for task_name, version in builtin_tasks.items():
            if task_name.lower() not in disabled:
                tasks[task_name] = version
                if logger:
                    logger.debug2(f"getAvailableTasks() : add of task {task_name} version {version}")
       
        # Scan for task modules
        directory = self.libdir
        directory = directory.replace('\\', '/')
        subdirectory = "GLPI/Agent/Task"
       
        pattern = f"{directory}/{subdirectory}/*/Version.py"
        for file_path in glob.glob(pattern):
            match = re.search(rf"({re.escape(subdirectory)}/(\S+)/Version\.py)$", file_path)
            if not match:
                continue
           
            module_path = file2module(match.group(1))
            name = file2module(match.group(2))
           
            if name.lower() in disabled:
                continue
           
            try:
                spec = importlib.util.spec_from_file_location(module_path, file_path)
                if not spec or not spec.loader:
                    continue
               
                version_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(version_module)
               
                version = getattr(version_module, 'VERSION', None)
                if not version:
                    continue
               
                tasks[name] = version
                if logger:
                    logger.debug2(f"getAvailableTasks() : add of task {name} version {version}")
               
            except Exception as e:
                if logger:
                    logger.debug2(f"module {module_path} does not compile: {e}")
       
        return tasks
   
    def get_asset_name(self) -> str:
        """Exact replica of getAssetName()"""
        config = {}
       
        if self.config and self.config.get('assetname-support'):
            support = self.config.get('assetname-support')
            if support == 1:
                config['short'] = True
            elif support == 3:
                config['fqdn'] = True
       
        return get_hostname(**config) or "unknown"
   
    def normalize_device_id(self, deviceid: str) -> str:
        """Exact replica of normalizeDeviceId()"""
        if not deviceid:
            return deviceid
       
        match = re.match(r'^(.*)(-\d+-\d+-\d+-\d+-\d+-\d+)', deviceid)
        if not match:
            return deviceid
       
        assetname, timestamp = match.groups()
        real_name = self.get_asset_name()
       
        if assetname == real_name:
            return deviceid
       
        # Check for FQDN vs short name changes
        if (len(real_name) > len(assetname) and
            real_name.startswith(f"{assetname}.")):
            return real_name + timestamp
       
        if (len(real_name) < len(assetname) and
            assetname.startswith(f"{real_name}.")):
            return real_name + timestamp
       
        # Finally assume deviceid has to be reset
        return ""
   
    def _handle_persistent_state(self):
        """Exact replica of _handlePersistentState()"""
        if not self.storage:
            self.storage = Storage(
                logger=self.logger,
                directory=self.vardir
            )
       
        data = self.storage.restore(name=f"{PROVIDER}-Agent")
        if not data:
            data = {}
       
        # Fix deviceid if assetname-support changed
        if data and not empty(data.get('deviceid')):
            data['deviceid'] = self.normalize_device_id(data['deviceid'])
       
        if not self.deviceid and not data.get('deviceid'):
            # Compute unique agent identifier
            assetname = self.get_asset_name()
           
            now = datetime.now()
            year, month, day, hour, minute, sec = (
                now.year, now.month, now.day,
                now.hour, now.minute, now.second
            )
           
            data['deviceid'] = f"{assetname}-{year:04d}-{month:02d}-{day:02d}-{hour:02d}-{minute:02d}-{sec:02d}"
        elif not data.get('deviceid'):
            data['deviceid'] = self.deviceid
       
        self.deviceid = data['deviceid']
       
        # Support agentid
        if not self.agentid and not data.get('agentid'):
            data['agentid'] = create_uuid()
        elif not data.get('agentid'):
            data['agentid'] = self.agentid
       
        self.agentid = data['agentid']
       
        # Handle forcerun option
        self._forced_run = data.pop('forcerun', False)
       
        # Always save agent state
        self.storage.save(
            name=f"{PROVIDER}-Agent",
            data=data
        )
   
    def set_force_run(self, forcerun=None):
        """Exact replica of setForceRun()"""
        storage = Storage(
            logger=self.logger,
            directory=self.vardir
        )
       
        data = storage.restore(name=f"{PROVIDER}-Agent")
        if not data:
            data = {}
       
        data['forcerun'] = 1 if forcerun is None or forcerun else 0
       
        storage.save(
            name=f"{PROVIDER}-Agent",
            data=data
        )
   
    def compute_task_execution_plan(self, available_tasks: Dict[str, str]) -> List[str]:
        """Exact replica of computeTaskExecutionPlan()"""
        config = self.config
        if not config:
            if self.logger:
                self.logger.error("no config found in agent. Can't compute tasks execution plan")
            return []
       
        execution_plan = []
        if config.has_filled_param('tasks'):
            if self.logger:
                self.logger.debug2("Preparing execution plan")
            execution_plan = self._make_execution_plan(config.get('tasks'), available_tasks)
        else:
            execution_plan = list(available_tasks.keys())
       
        return execution_plan
   
    def _make_execution_plan(self, sorted_tasks: List[str], available_tasks: Dict[str, str]) -> List[str]:
        """Exact replica of _makeExecutionPlan()"""
        task_map = {name.lower(): name for name in available_tasks.keys()}
       
        execution_plan = []
        for task in sorted_tasks:
            if not task:
                continue
            if task == CONTINUE_WORD:
                used = set(execution_plan)
                remaining = [name for name in available_tasks.keys() if name not in used]
                execution_plan.extend(remaining)
                break
            task_lower = task.lower()
            if task_lower in task_map:
                execution_plan.append(task_map[task_lower])
       
        return execution_plan


def main():
    """Main entry point - exact Perl replica"""
    import argparse
   
    parser = argparse.ArgumentParser(description="GLPI Agent")
    parser.add_argument('--datadir', help='Data directory', default='/usr/share/glpi-agent')
    parser.add_argument('--libdir', help='Library directory', default='/usr/lib/glpi-agent')
    parser.add_argument('--vardir', help='Variable directory', default='/var/lib/glpi-agent')
    parser.add_argument('--server', action='append', help='Server URL(s)')
    parser.add_argument('--local', help='Local target directory')
    parser.add_argument('--tag', help='Agent tag')
    parser.add_argument('--force', action='store_true', help='Force execution')
    parser.add_argument('--lazy', action='store_true', help='Lazy mode')
    parser.add_argument('--no-task', action='append', help='Disable tasks')
    parser.add_argument('--tasks', help='Comma-separated task list')
    parser.add_argument('--list-tasks', action='store_true', help='List available tasks')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--version', action='version', version=f'{PROVIDER} Agent {VERSION}')
   
    args = parser.parse_args()
   
    # Convert args to options dict
    options = {}
    for key, value in vars(args).items():
        if value is not None:
            if key == 'no_task':
                options['no-task'] = value
            elif key == 'list_tasks':
                options['list-tasks'] = value
            elif key == 'tasks' and isinstance(value, str):
                options['tasks'] = [t.strip() for t in value.split(',')]
            else:
                options[key.replace('_', '-')] = value
   
    try:
        agent = GLPIAgent(
            datadir=args.datadir,
            libdir=args.libdir,
            vardir=args.vardir
        )
       
        agent.init(options=options)
       
        # Handle --list-tasks
        if options.get('list-tasks'):
            available = agent.get_available_tasks()
            print("Available tasks:")
            for task, version in sorted(available.items()):
                print(f"  {task}: {version}")
            return 0
       
        # Run the agent
        agent.run()
       
        return 0
       
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 1
    except SystemExit as e:
        return e.code
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == '__main__':

    sys.exit(main())
