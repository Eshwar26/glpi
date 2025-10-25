"""
GLPI Agent Task Collect Module

This module handles data collection tasks from the GLPI server.
"""

import hashlib
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Callable, Optional

from GLPI.Agent.Task.Collect.Version import VERSION

__version__ = VERSION


# Validation constants
_OPTIONAL = 0
_MANDATORY = 1
_OPTIONAL_EXCLUSIVE = 2


class CollectTask:
    """GLPI Agent Collect Task"""
    
    def __init__(self, logger=None, config=None, target=None, deviceid=None):
        """Initialize the Collect task"""
        self.logger = logger
        self.config = config
        self.target = target
        self.deviceid = deviceid
        self.client = None
        
        # Function mapping
        self.functions: Dict[str, Callable] = {
            'getFromRegistry': self._get_from_registry,
            'findFile': self._find_file,
            # As decided by developers team, the runCommand function is disabled for the moment.
            # 'runCommand': self._run_command,
            'getFromWMI': self._get_from_wmi
        }
        
        # JSON validation rules
        self.json_validation = {
            'getFromRegistry': {
                'path': _MANDATORY
            },
            'findFile': {
                'dir': _MANDATORY,
                'limit': _MANDATORY,
                'recursive': _MANDATORY,
                'filter': {
                    'regex': _OPTIONAL,
                    'sizeEquals': _OPTIONAL,
                    'sizeGreater': _OPTIONAL,
                    'sizeLower': _OPTIONAL,
                    'checkSumSHA512': _OPTIONAL,
                    'checkSumSHA2': _OPTIONAL,
                    'name': _OPTIONAL,
                    'iname': _OPTIONAL,
                    'is_file': _MANDATORY,
                    'is_dir': _MANDATORY
                }
            },
            'getFromWMI': {
                'class': _MANDATORY,
                'properties': _MANDATORY
            }
        }

    def is_enabled(self) -> bool:
        """Check if the task is enabled"""
        if not self.target or not self.target.is_type('server'):
            if self.logger:
                self.logger.debug("Collect task only compatible with server target")
            return False
        
        return True

    def _validate_spec(self, base: Dict, key: str, spec: Any) -> bool:
        """Validate specification for a job parameter"""
        if isinstance(spec, dict):
            if key not in base:
                if self.logger:
                    self.logger.debug(f"{key} mandatory values are missing in job")
                return False
            
            if self.logger:
                self.logger.debug2(f"{key} mandatory values are present in job")
            
            for attribute, attr_spec in spec.items():
                if not self._validate_spec(base[key], attribute, attr_spec):
                    return False
            return True
        
        if spec == _MANDATORY:
            if key not in base:
                if self.logger:
                    self.logger.debug(f"{key} mandatory value is missing in job")
                return False
            
            if self.logger:
                self.logger.debug2(f"{key} mandatory value is present in job")
            return True
        
        if spec == _OPTIONAL and key in base:
            if self.logger:
                self.logger.debug2(f"{key} optional value is present in job")
        
        return True

    def _validate_answer(self, answer: Optional[Dict]) -> bool:
        """Validate the answer from the server"""
        if answer is None:
            if self.logger:
                self.logger.debug("Bad JSON: No answer from server.")
            return False
        
        if not isinstance(answer, dict):
            if self.logger:
                self.logger.debug("Bad JSON: Bad answer from server. Not a dictionary.")
            return False
        
        if 'jobs' not in answer or not isinstance(answer['jobs'], list):
            if self.logger:
                self.logger.debug("Bad JSON: Missing jobs")
            return False
        
        for job in answer['jobs']:
            # Check for required keys
            for required_key in ['uuid', 'function']:
                if required_key not in job:
                    if self.logger:
                        self.logger.debug(f"Bad JSON: Missing key '{required_key}' in job")
                    return False
            
            function = job['function']
            if function not in self.functions:
                if self.logger:
                    self.logger.debug("Bad JSON: not supported 'function' key value in job")
                return False
            
            if function not in self.json_validation:
                if self.logger:
                    self.logger.debug("Bad JSON: Can't validate job")
                return False
            
            for attribute, spec in self.json_validation[function].items():
                if not self._validate_spec(job, attribute, spec):
                    if self.logger:
                        self.logger.debug(f"Bad JSON: '{function}' job JSON format is not valid")
                    return False
        
        return True

    def run(self) -> Optional[bool]:
        """Run the collect task"""
        # Just reset event if run as an event to not trigger another one
        if hasattr(self, 'reset_event'):
            self.reset_event()
        
        # Initialize HTTP client (would need to import the actual client class)
        # self.client = GLPIAgentHTTPClientFusion(logger=self.logger, config=self.config)
        
        if not self.target:
            return None
        
        # Get configuration from server
        global_remote_config = None
        # In a real implementation, this would send an HTTP request:
        # global_remote_config = self.client.send(
        #     url=self.target.get_url(),
        #     args={
        #         'action': 'getConfig',
        #         'machineid': self.deviceid,
        #         'task': {'Collect': VERSION}
        #     }
        # )
        
        target_id = self.target.id() if hasattr(self.target, 'id') else 'unknown'
        
        if not global_remote_config:
            if self.logger:
                self.logger.info(f"Collect task not supported by {target_id}")
            return None
        
        if 'schedule' not in global_remote_config:
            if self.logger:
                self.logger.info(f"No job schedule returned by {target_id}")
            return None
        
        if not isinstance(global_remote_config['schedule'], list):
            if self.logger:
                self.logger.info(f"Malformed schedule from {target_id}")
            return None
        
        if not global_remote_config['schedule']:
            if self.logger:
                self.logger.info("No Collect job enabled or Collect support disabled server side.")
            return None
        
        run_jobs = 0
        for job in global_remote_config['schedule']:
            if isinstance(job, dict) and job.get('task') == 'Collect':
                self._process_remote(job.get('remote'))
                run_jobs += 1
        
        if run_jobs == 0:
            if self.logger:
                self.logger.info("No Collect job found in server jobs list.")
            return None
        
        return True

    def _process_remote(self, remote_url: Optional[str]) -> Optional['CollectTask']:
        """Process remote jobs from the server"""
        if not remote_url:
            return None
        
        # Get jobs from server
        answer = None
        # In real implementation:
        # answer = self.client.send(
        #     url=remote_url,
        #     args={
        #         'action': 'getJobs',
        #         'machineid': self.deviceid
        #     }
        # )
        
        if isinstance(answer, dict) and not answer:
            if self.logger:
                self.logger.debug("Nothing to do")
            return None
        
        if not self._validate_answer(answer):
            return None
        
        jobs = answer.get('jobs', [])
        if not jobs:
            raise Exception("no jobs provided, aborting")
        
        method = 'POST' if answer.get('postmethod') == 'POST' else 'GET'
        token = answer.get('token', '')
        has_csrf_token = bool(token)
        jobs_done = {}
        
        for job in jobs:
            if self.logger:
                self.logger.debug2("Starting a collect job...")
            
            if 'uuid' not in job:
                if self.logger:
                    self.logger.error("UUID key missing")
                continue
            
            if self.logger:
                self.logger.debug2(f"Collect job has uuid: {job['uuid']}")
            
            if 'function' not in job:
                if self.logger:
                    self.logger.error("function key missing")
                continue
            
            function_name = job['function']
            if function_name not in self.functions:
                if self.logger:
                    self.logger.error(f"Bad function '{function_name}'")
                continue
            
            # Call the function
            results = self.functions[function_name](logger=self.logger, **job)
            
            count = len(results)
            
            # Add an empty dict so we send an answer with _cpt=0
            if not count:
                results.append({})
                count = 1
            
            for result in results:
                if not isinstance(result, dict):
                    continue
                if count > 0 and not result:
                    continue
                
                result['uuid'] = job['uuid']
                result['action'] = 'setAnswer'
                result['_cpt'] = count
                
                if token:
                    result['_glpi_csrf_token'] = token
                
                if '_sid' in job:
                    result['_sid'] = job['_sid']
                
                # Send result to server
                # answer = self.client.send(
                #     url=remote_url,
                #     method=method,
                #     filename=f"collect_{job['uuid']}_{count}.js",
                #     args=result
                # )
                answer = {}  # Placeholder
                
                token = answer.get('token', '') if answer else ''
                count -= 1
                
                # Handle CSRF access denied
                if has_csrf_token and not token:
                    if self.logger:
                        self.logger.error("Bad answer: CSRF checking is failing")
                    
                    # Send empty answer to force error on server job
                    # self.client.send(
                    #     url=remote_url,
                    #     args={
                    #         'uuid': job['uuid'],
                    #         'action': 'setAnswer'
                    #     }
                    # )
                    
                    # Send last message for server job log
                    # self.client.send(
                    #     url=remote_url,
                    #     args={
                    #         'uuid': job['uuid'],
                    #         'action': 'setAnswer',
                    #         'csrf_failure': 1
                    #     }
                    # )
                    
                    # No need to send job done message
                    if job['uuid'] in jobs_done:
                        del jobs_done[job['uuid']]
                    break  # Exit job loop
            
            # Mark this job as done
            jobs_done[job['uuid']] = True
        
        # Finally send jobsDone for each seen jobs uuid
        for uuid in jobs_done:
            # answer = self.client.send(
            #     url=remote_url,
            #     args={
            #         'action': 'jobsDone',
            #         'uuid': uuid
            #     }
            # )
            answer = None  # Placeholder
            
            if not answer and self.logger:
                self.logger.debug2(f"Got no response on {uuid} jobsDone action")
        
        return self

    @staticmethod
    def _encode_registry_value_for_collect(value: Any, reg_type: Optional[int] = None) -> str:
        """
        Encode registry values for collection.
        Dump REG_BINARY/REG_RESOURCE_LIST/REG_FULL_RESOURCE_DESCRIPTOR as hex strings
        """
        # Registry type constants
        REGISTRY_TYPES = [
            'REG_NONE', 'REG_SZ', 'REG_EXPAND_SZ', 'REG_BINARY', 'REG_DWORD',
            'REG_DWORD_BIG_ENDIAN', 'REG_LINK', 'REG_MULTI_SZ', 'REG_RESOURCE_LIST',
            'REG_FULL_RESOURCE_DESCRIPTOR', 'REG_RESOURCE_REQUIREMENTS_LIST', 'REG_QWORD'
        ]
        
        if reg_type is not None and (reg_type == 3 or reg_type >= 8):
            # Convert to hex string
            if isinstance(value, bytes):
                value = ' '.join(f'{b:02x}' for b in value)
            elif isinstance(value, str):
                value = ' '.join(f'{ord(c):02x}' for c in value)
        
        return str(value) if value is not None else ''

    def _get_from_registry(self, logger=None, path=None, **kwargs) -> List[Dict]:
        """
        Get values from Windows Registry.
        Windows-specific functionality.
        """
        # Registry type names for debugging
        registry_types = [
            'REG_NONE', 'REG_SZ', 'REG_EXPAND_SZ', 'REG_BINARY', 'REG_DWORD',
            'REG_DWORD_BIG_ENDIAN', 'REG_LINK', 'REG_MULTI_SZ', 'REG_RESOURCE_LIST',
            'REG_FULL_RESOURCE_DESCRIPTOR', 'REG_RESOURCE_REQUIREMENTS_LIST', 'REG_QWORD'
        ]
        
        # Check if Windows platform is available
        try:
            import platform
            if platform.system() != 'Windows':
                return []
            
            # Would need to import Windows registry tools
            # from GLPI.Agent.Tools.Win32 import get_registry_value
        except ImportError:
            return []
        
        if logger:
            logger.debug(f"Looking for '{path}' registry key...")
        
        # In a real implementation, this would call the Windows registry API
        # values = get_registry_value(path=path, withtype=True)
        values = None  # Placeholder
        
        if not values:
            return []
        
        result = {}
        
        if isinstance(values, dict):
            for k, v in values.items():
                # Skip sub keys
                if k.endswith('/'):
                    continue
                
                value, reg_type = v
                result[k] = self._encode_registry_value_for_collect(value, reg_type)
                
                if logger and reg_type < len(registry_types):
                    logger.debug2(f"Found {registry_types[reg_type]} value: {result[k]}")
        else:
            # Extract key name from path
            match = re.search(r'([^/]+)$', path)
            k = match.group(1) if match else 'value'
            
            value, reg_type = values
            
            if isinstance(value, list):
                encoded_values = [self._encode_registry_value_for_collect(v) for v in value]
                result[k] = ','.join(encoded_values)
                
                if logger and reg_type < len(registry_types):
                    for v in value:
                        logger.debug2(f"Found {registry_types[reg_type]} value: {v}")
            else:
                result[k] = self._encode_registry_value_for_collect(value, reg_type)
                
                if logger and reg_type < len(registry_types):
                    logger.debug2(f"Found {registry_types[reg_type]} value: {result[k]}")
        
        return [result]

    def _find_file(self, logger=None, dir='/', limit=50, recursive=False, 
                   filter=None, **kwargs) -> List[Dict]:
        """
        Find files matching specified criteria.
        
        Args:
            logger: Logger instance
            dir: Directory to search in
            limit: Maximum number of results
            recursive: Whether to search recursively
            filter: Dictionary of filter criteria
        
        Returns:
            List of dictionaries with 'size' and 'path' keys
        """
        if filter is None:
            filter = {}
        
        search_dir = Path(dir)
        if not search_dir.exists() or not search_dir.is_dir():
            return []
        
        if logger:
            logger.debug(f"Looking for file under '{dir}' folder")
        
        results = []
        
        def check_file(file_path: Path) -> bool:
            """Check if file matches all filters"""
            # Check directory filter
            is_dir_filter = filter.get('is_dir', False)
            is_file_filter = filter.get('is_file', False)
            checksum_sha512 = filter.get('checkSumSHA512')
            checksum_sha2 = filter.get('checkSumSHA2')
            checksum_sha256 = filter.get('checkSumSHA256')
            
            if is_dir_filter and not checksum_sha512 and not checksum_sha2:
                if not file_path.is_dir():
                    return False
            
            if is_file_filter:
                if not file_path.is_file():
                    return False
            
            filename = file_path.name
            
            # Name filter (case-sensitive)
            if 'name' in filter:
                if filename != filter['name']:
                    return False
            
            # Name filter (case-insensitive)
            if 'iname' in filter:
                if filename.lower() != filter['iname'].lower():
                    return False
            
            # Regex filter
            if 'regex' in filter:
                if not re.search(filter['regex'], str(file_path)):
                    return False
            
            # Get file size
            try:
                size = file_path.stat().st_size
            except (OSError, IOError):
                return False
            
            # Size filters
            if 'sizeEquals' in filter:
                if size != filter['sizeEquals']:
                    return False
            
            if 'sizeGreater' in filter:
                if size < filter['sizeGreater']:
                    return False
            
            if 'sizeLower' in filter:
                if size > filter['sizeLower']:
                    return False
            
            # SHA512 checksum filter
            if checksum_sha512:
                try:
                    with open(file_path, 'rb') as f:
                        sha512 = hashlib.sha512(f.read()).hexdigest()
                        if sha512 != checksum_sha512.lower():
                            return False
                except (OSError, IOError):
                    return False
            
            # SHA256 checksum filter (checkSumSHA2 is historic, was sha256)
            expected_sha256 = checksum_sha256 or checksum_sha2
            if expected_sha256:
                try:
                    with open(file_path, 'rb') as f:
                        sha256 = hashlib.sha256(f.read()).hexdigest()
                        if sha256 != expected_sha256.lower():
                            return False
                except (OSError, IOError):
                    return False
            
            # All filters passed
            if logger:
                logger.debug2(f"Found file: {file_path}")
            
            results.append({
                'size': size,
                'path': str(file_path)
            })
            
            return True
        
        # Traverse directory
        if recursive:
            for file_path in search_dir.rglob('*'):
                check_file(file_path)
                if len(results) >= limit:
                    break
        else:
            for file_path in search_dir.iterdir():
                check_file(file_path)
                if len(results) >= limit:
                    break
        
        return results

    def _run_command(self, logger=None, command=None, filter=None, **kwargs) -> List[Dict]:
        """
        Run a command and return output.
        NOTE: This function is currently disabled by the development team.
        
        Args:
            logger: Logger instance
            command: Command to execute
            filter: Filter to apply to output
        
        Returns:
            List with dictionary containing 'output' key
        """
        if filter is None:
            filter = {}
        
        # This functionality is disabled
        # In a real implementation, would execute command and filter output
        
        import subprocess
        
        line = ''
        
        try:
            if 'firstMatch' in filter:
                # Get first matching line
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                pattern = filter['firstMatch']
                for output_line in result.stdout.splitlines():
                    if re.search(pattern, output_line):
                        line = output_line
                        break
            
            elif 'firstLine' in filter:
                # Get first line
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                lines = result.stdout.splitlines()
                line = lines[0] if lines else ''
            
            elif 'lineCount' in filter:
                # Get line count
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                line = str(len(result.stdout.splitlines()))
            
            else:
                # Get all lines
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                line = result.stdout
        
        except Exception as e:
            if logger:
                logger.error(f"Error running command: {e}")
            line = ''
        
        return [{'output': line}]

    def _get_from_wmi(self, logger=None, properties=None, wmi_class=None, 
                     **kwargs) -> List[Dict]:
        """
        Get data from Windows Management Instrumentation (WMI).
        Windows-specific functionality.
        
        Args:
            logger: Logger instance
            properties: List of properties to retrieve or comma-separated string
            wmi_class: WMI class to query (passed as 'class' in kwargs)
        
        Returns:
            List of dictionaries containing WMI object data
        """
        # Get the class parameter (renamed from 'class' which is a Python keyword)
        wmi_class = kwargs.get('class', wmi_class)
        
        # Check if Windows platform is available
        try:
            import platform
            if platform.system() != 'Windows':
                return []
            
            # Would need to import Windows WMI tools
            # from GLPI.Agent.Tools.Win32 import get_wmi_objects
        except ImportError:
            return []
        
        if not properties or not wmi_class:
            return []
        
        # Split given properties if it's a comma or space-separated string
        if isinstance(properties, list) and len(properties) == 1:
            if re.search(r'[, ]+', properties[0]):
                properties = re.split(r'[, ]+', properties[0])
        elif isinstance(properties, str):
            if re.search(r'[, ]+', properties):
                properties = re.split(r'[, ]+', properties)
            else:
                properties = [properties]
        
        results = []
        
        # In a real implementation, this would query WMI:
        # objects = get_wmi_objects(class=wmi_class, properties=properties)
        # for obj in objects:
        #     results.append(obj)
        
        return results
