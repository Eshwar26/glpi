"""
GLPI Agent HTTP Server ToolBox Inventory - Python Implementation

This module provides inventory task management for the GLPI Agent toolbox.
"""

import re
import time
import random
import os
from typing import Optional, Dict, Any, List, Tuple
from html import escape
from urllib.parse import unquote

from glpi_agent_logger import Logger
from glpi_agent_tools import empty, first
from glpi_agent_target import Target
from glpi_agent_event import Event


class ToolBoxInventory:
    """
    Inventory toolbox plugin for GLPI Agent.
    
    Manages network scanning, local inventory tasks, and job scheduling.
    """
    
    INVENTORY = "inventory"
    JOBS = "jobs"
    NEED_INIT = True
    
    def __init__(self, toolbox=None, **params):
        """
        Initialize the inventory toolbox.
        
        Args:
            toolbox: Parent toolbox instance
            **params: Additional parameters
        """
        # Extract class name
        class_name = self.__class__.__name__
        
        self.logger = (toolbox.get('logger') if toolbox else None) or Logger()
        self.toolbox = toolbox
        self.name = class_name
        self.tasks = {}
        
        self._scan = 0
        self._local = 0
        self._missingdep = 0
        self._not_before = {}
        self.threads_default = 1
        self.timeout_default = 1
        self.targets = {}
        self.taskid = None
        self.verbosity = 'debug'
        
        # Check for missing dependencies
        try:
            # Import NetDiscovery task
            from glpi_agent_task_netdiscovery import NetDiscovery
        except ImportError:
            self._missingdep = 1
        
        try:
            # Import NetInventory task
            from glpi_agent_task_netinventory import NetInventory
        except ImportError:
            self._missingdep += 2
    
    @classmethod
    def index(cls):
        """Return the index identifier."""
        return cls.INVENTORY
    
    def log_prefix(self):
        """Return the log prefix."""
        return "[toolbox plugin, inventory] "
    
    def init(self):
        """Initialize the plugin."""
        if not self.read_yaml():
            return
        
        # Update networktask_save folder if running as a service
        yaml_config = self.yaml('configuration') or {}
        networktask_save = yaml_config.get('networktask_save', '.')
        
        if empty(networktask_save) or networktask_save == '.':
            agent = self.toolbox.get('server', {}).get('agent')
            if agent:
                is_service = (
                    (os.name == 'nt' and agent.__class__.__name__ == 'Win32Daemon') or
                    os.getppid() == 1
                )
                if is_service:
                    yaml_config['networktask_save'] = agent.get('vardir')
                    self.need_save("configuration")
                    self.write_yaml()
        
        self._load_jobs()
    
    def yaml_config_specs(self, yaml_config):
        """
        Return YAML configuration specifications.
        
        Args:
            yaml_config: Current YAML configuration
            
        Returns:
            Dictionary of configuration specifications
        """
        updating_support = self.isyes(yaml_config.get('updating_support'))
        inventory_navbar = self.isyes(yaml_config.get('inventory_navbar', 1))
        
        return {
            'inventory_navbar': {
                'category': "Navigation bar",
                'type': "bool" if updating_support else "readonly",
                'value': self.yesno(inventory_navbar),
                'text': "Show Inventory tasks in navigation bar",
                'navbar': "Inventory tasks",
                'link': self.index(),
                'icon': "subtask",
                'index': 10,
            },
            'threads_options': {
                'category': "Network task",
                'type': "text" if updating_support else "readonly",
                'value': yaml_config.get('threads_options', '1|5|10|20|40'),
                'text': "Network task threads number options",
                'tips': "threads number options separated by pipes,\nfirst value used as default threads\n(default=1|5|10|20|40)",
                'only_if': inventory_navbar,
            },
            'timeout_options': {
                'category': "Network task",
                'type': "text" if updating_support else "readonly",
                'value': yaml_config.get('timeout_options', '1|2|5|10|30|60'),
                'text': "Network task timeout options",
                'tips': "Timeout options separated by pipes,\nfirst value used as default timeout\n(default=1|2|5|10|30|60)",
                'only_if': inventory_navbar,
            },
            'networktask_save': {
                'category': "Network task",
                'type': "text" if updating_support else "readonly",
                'value': yaml_config.get('networktask_save', '.'),
                'text': "Base folder to save inventory files",
                'tips': "Base folder may be relative to the agent folder",
                'only_if': inventory_navbar,
            },
            'inventory_tags': {
                'category': "Inventories",
                'type': "text",
                'value': yaml_config.get('inventory_tags', ''),
                'text': "List of tags",
                'tips': "Tags separated by commas\nYou can use it to separate inventory files by site",
                'only_if': inventory_navbar,
            },
        }
    
    def update_template_hash(self, hash_data):
        """
        Update template hash with current data.
        
        Args:
            hash_data: Hash dictionary to update
        """
        if not hash_data:
            return
        
        yaml_data = self.yaml() or {}
        jobs = self.yaml(self.JOBS) or {}
        ip_range = self.yaml('ip_range') or {}
        yaml_config = self.yaml('configuration') or {}
        
        # Update template hash with encoded values
        for base in ['ip_range', 'jobs', 'scheduling']:
            hash_data[base] = {}
            if base not in yaml_data:
                continue
            
            for name, entry in yaml_data[base].items():
                hash_data[base][name] = {}
                for key, value in entry.items():
                    if value is None:
                        continue
                    
                    if key in ['name', 'ip_range', 'description']:
                        value = escape(value)
                    elif key == 'enabled':
                        value = self.isyes(value)
                    
                    hash_data[base][name][key] = value
        
        # Don't include listing data when editing
        if not self.edit():
            hash_data['columns'] = [
                {'name': "Task name"},
                {'type': "Type"},
                {'scheduling': "Scheduling"},
                {'last_run_date': "Last run date"},
                {'next_run_date': "Next run date"},
                {'config': "Configuration"},
                {'description': "Description"}
            ]
            
            hash_data['order'] = self.get_from_session('jobs_order') or "ascend"
            asc = hash_data['order'] == 'ascend'
            ordering = hash_data['ordering_column'] = self.get_from_session('jobs_ordering_column') or 'name'
            
            # Include netscan tasks run from results page
            tasks = self.tasks or {}
            for taskid, task in tasks.items():
                if task.get('name') and task['name'] not in jobs:
                    name = task['name']
                    hash_data['jobs'][name] = {
                        'name': name,
                        'last_run_date': task.get('time'),
                        'enabled': False,
                        'type': "netscan",
                        'config': {
                            'ip_range': task.get('ip_ranges'),
                            'ip': task.get('ip'),
                        },
                    }
            
            jobs = hash_data['jobs']
            
            # Sort jobs
            def sort_key(name):
                A, B = (name, name)
                if ordering == 'name':
                    return name
                elif ordering == 'last_run_date':
                    return (jobs[name].get(ordering, 0), name)
                elif ordering == 'next_run_date':
                    val = jobs[name].get(ordering, 0)
                    if not self.isyes(jobs[name].get('enabled')):
                        val = jobs[name].get('last_run_date', 0)
                    return (val, name)
                elif ordering == 'scheduling':
                    sched = jobs[name].get(ordering)
                    val = sched[0] if sched else ''
                    return (val, name)
                elif ordering == 'config':
                    config = jobs[name].get(ordering)
                    val = config.get('target', '') if config else ''
                    return (val, name)
                else:
                    return (jobs[name].get(ordering, ''), name)
            
            hash_data['jobs_order'] = sorted(jobs.keys(), key=sort_key, reverse=not asc)
            
            display_options_str = yaml_config.get('display_options', '30|0|5|10|20|40|50|100|500')
            display_options = sorted(set(int(x) for x in display_options_str.split('|') if x.isdigit()))
            hash_data['display_options'] = display_options
            
            display = self.get_from_session('display')
            hash_data['display'] = int(display) if display else (display_options[0] if display_options else 0)
            
            hash_data['iprange_options'] = sorted([escape(k) for k in ip_range.keys()])
            hash_data['list_count'] = len(jobs)
            
            if not hash_data['display']:
                self.delete_in_session('jobs_start')
            
            start = self.get_from_session('jobs_start') or 1
            start = min(start, hash_data['list_count']) if hash_data['list_count'] else start
            
            hash_data['start'] = start
            hash_data['page'] = int((start-1)/hash_data['display'])+1 if hash_data['display'] else 1
            hash_data['pages'] = int((hash_data['list_count']-1)/hash_data['display'])+1 if hash_data['display'] else 1
            hash_data['start'] = start - start % hash_data['display'] if hash_data['display'] else 0
            
            if hash_data['start'] == hash_data['list_count']:
                hash_data['start'] -= hash_data['display']
            hash_data['start'] = max(0, hash_data['start'])
        
        # Set missing deps
        hash_data['missingdeps'] = self._missingdep or ''
        
        # Set known targets
        agent = self.toolbox.get('server', {}).get('agent')
        self.targets = hash_data['targets'] = {}
        if agent:
            for target in agent.getTargets():
                if target.isType('listener'):
                    continue
                target_id = target.id()
                if not target_id:
                    continue
                hash_data['targets'][target_id] = [
                    target.getType(),
                    target.getFullPath() if target.isType('local') else target.getName()
                ]
        
        hash_data['default_target'] = 'server0' if 'server0' in hash_data['targets'] else ''
        hash_data['default_local'] = yaml_config.get('networktask_save', '.')
        
        # Set running task
        hash_data['outputid'] = self.taskid or ''
        hash_data['tasks'] = self.tasks or {}
        hash_data['verbosity'] = self.verbosity or 'debug'
        
        threads_options_str = yaml_config.get('threads_options', '1|5|10|20|40')
        threads_options = sorted(set(int(x) for x in threads_options_str.split('|') if x.isdigit()))
        hash_data['threads_options'] = threads_options
        self.threads_default = threads_options[0] if threads_options else 1
        hash_data['threads_option'] = self.get_from_session('netscan_threads_option') or self.threads_default
        
        timeout_options_str = yaml_config.get('timeout_options', '1|10|30|60')
        timeout_options = sorted(set(int(x) for x in timeout_options_str.split('|') if x.isdigit()))
        hash_data['timeout_options'] = timeout_options
        self.timeout_default = timeout_options[0] if timeout_options else 1
        hash_data['timeout_option'] = self.get_from_session('netscan_timeout_option') or self.timeout_default
        
        tag_options = yaml_config.get('inventory_tags', '').split(',') if yaml_config.get('inventory_tags') else []
        hash_data['tag_options'] = tag_options
        hash_data['current_tag'] = self.get_from_session('inventory_tag')
        hash_data['title'] = "Inventory tasks"
    
    def _task_id(self):
        """Generate a unique task ID."""
        while True:
            taskid = '-'.join(f"{random.randint(0, 65535):04x}" for _ in range(4))
            if taskid not in self.tasks:
                return taskid
    
    def register_events_cb(self):
        """Register events callback."""
        return True
    
    def events_cb(self, event=None):
        """
        Handle events callback.
        
        Args:
            event: Event to handle
            
        Returns:
            True if event was handled, False otherwise
        """
        # Implementation would continue here with event handling logic
        # This is a partial conversion due to the complexity
        return False
    
    def ajax_support(self):
        """Check if AJAX is supported."""
        return True
    
    def ajax(self, query):
        """
        Handle AJAX requests.
        
        Args:
            query: Query string
            
        Returns:
            Tuple of (status_code, status_text, headers, body)
        """
        # Parse query
        query_params = {'debug': True}
        if query:
            self.debug2(f"Got inventory ajax query: {query}")
            for param in query.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    query_params[key] = value
                else:
                    query_params[param] = True
        
        taskid = query_params.get('id')
        if not taskid:
            return None
        
        task = self.tasks.get(taskid)
        if not task:
            return None
        
        # Set filter based on verbosity
        if query_params.get('debug2'):
            filter_pattern = None
        elif query_params.get('info'):
            filter_pattern = re.compile(r'^\[(?:error|info|warning)\]')
        else:
            filter_pattern = re.compile(r'^\[(?:error|info|warning|debug)\]')
        
        # Set default taskid
        self.taskid = taskid
        
        headers = {
            'Content-Type': 'text/plain',
            'X-Inventory-Output': 'partial',
            'X-Inventory-Status': 'running',
            'X-Inventory-Count': str(task.get('inventory_count', 0)),
            'X-Inventory-Percent': str(task.get('percent', 0)),
            'X-Inventory-Task': taskid,
            'Connection': 'close',
        }
        
        if task.get('islocal'):
            headers['X-Inventory-IsLocal'] = str(task['islocal'])
        else:
            if task.get('snmp_support'):
                headers['X-Inventory-With-SNMP'] = str(task['snmp_support'])
            if task.get('others_support'):
                headers['X-Inventory-With-Others'] = str(task['others_support'])
            if task.get('count'):
                headers['X-Inventory-Scanned'] = str(task['count'])
            if task.get('unknown'):
                headers['X-Inventory-Unknown'] = str(task['unknown'])
            if task.get('maxcount'):
                headers['X-Inventory-MaxCount'] = str(task['maxcount'])
        
        agent = self.toolbox.get('server', {}).get('agent')
        if task.get('done') or (agent and not agent.forked(name=task.get('procname'))):
            headers['X-Inventory-Status'] = 'done'
        
        what = query_params.get('what')
        if what == 'full':
            headers['X-Inventory-Output'] = 'full'
            task['index'] = 0
        elif what == 'abort' and task.get('percent', 0) < 100:
            self.debug2(f"Abort request for: {task['name']}")
            if agent:
                agent.abort_child(taskid)
        elif what == 'status':
            # Set last/next run dates
            jobs = self.yaml(self.JOBS) or {}
            job = jobs.get(task.get('name'), {})
            last_run = job.get('last_run_date') or task.get('time')
            if last_run:
                headers['X-Inventory-LastRunDate'] = time.ctime(last_run)
            if self.isyes(job.get('enabled')) and job.get('next_run_date'):
                headers['X-Inventory-NextRunDate'] = time.ctime(job['next_run_date'])
                headers['X-Inventory-NextRunTime'] = str(job['next_run_date'])
        
        if task.get('aborted'):
            headers['X-Inventory-Status'] = 'aborted'
        if task.get('failed'):
            headers['X-Inventory-Status'] = 'failed'
        
        message = ''
        if what != 'status':
            index = int(query_params.get('index', task.get('index', 0)))
            messages = task.get('messages', [])
            
            while index < len(messages):
                line_feed = "\n" if index else ""
                this_msg = messages[index]
                index += 1
                
                if not filter_pattern or filter_pattern.search(this_msg):
                    message += line_feed + this_msg
            
            task['index'] = index
            headers['X-Inventory-Index'] = str(index)
            
            if not index and not message:
                message = '...'
        
        return 200, 'OK', headers, message
    
    # Additional helper methods would be implemented here
    # (read_yaml, write_yaml, yaml, need_save, get_from_session, etc.)
    
    def _get_next_run_date(self, name, job, not_before=None):
        """
        Calculate next run date for a job.
        
        Args:
            name: Job name
            job: Job configuration
            not_before: Minimum start time
            
        Returns:
            Next run timestamp
        """
        if not job:
            return None
        
        if not self._not_before:
            self._not_before = {}
        
        if not_before is None:
            not_before = self._not_before.get(name, 0)
        
        last = job.get('last_run_date', 0)
        scheduling = self.yaml('scheduling') or {}
        
        weekdays = {'sun': 0, 'mon': 1, 'tue': 2, 'wed': 3, 'thu': 4, 'fri': 5, 'sat': 6}
        
        delays = []
        
        for schedule in job.get('scheduling', []):
            sched = scheduling.get(schedule)
            if not sched or not sched.get('type'):
                continue
            
            now = int(time.time())
            
            if sched['type'] == 'delay' and sched.get('delay'):
                match = re.match(r'^(\d+)(s|m|h|d|w)$', sched['delay'])
                if not match:
                    continue
                
                delay_value, unit = match.groups()
                delay_value = int(delay_value)
                
                multiplier = {
                    's': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 7*86400
                }.get(unit, 1)
                
                delay = delay_value * multiplier
                next_start = last + delay
                next_start = max(next_start, not_before)
                
                if delay >= 86400:
                    fuzzy = random.randint(-1800, 1800)
                elif delay >= 3600:
                    fuzzy = random.randint(-150, 150)
                elif delay >= 120:
                    fuzzy = random.randint(-5, 5)
                else:
                    fuzzy = 0
                
                if next_start + fuzzy < now:
                    next_start = now
                    fuzzy = random.randint(0, min(delay, 60) if delay > 60 else delay)
                
                delays.append({
                    'start': next_start + fuzzy,
                    'not_before': next_start + delay,
                })
        
        # Choose soonest delay
        if not delays:
            return None
        
        rundate = min(delays, key=lambda x: x['start'])
        
        # Keep not_before for next run date request
        self._not_before[name] = rundate['not_before']
        
        return rundate['start']
    
    def _load_jobs(self):
        """Load and schedule jobs from YAML configuration."""
        jobs = self.yaml(self.JOBS) or {}
        target = self.toolbox.get('target')
        
        if not target:
            return
        
        for name, job in jobs.items():
            if not job or not self.isyes(job.get('enabled')):
                continue
            
            event_data = {
                'job': True,
                'name': name,
                'task': "inventory" if job.get('type') == 'local' else "netscan",
            }
            event = Event(**event_data)
            
            if job.get('next_run_date') and job['next_run_date'] > time.time():
                event.rundate(job['next_run_date'])
            else:
                rundate = self._get_next_run_date(name, job)
                event.rundate(rundate)
                job['next_run_date'] = rundate
                self.need_save(self.JOBS)
            
            target.delEvent(event)
            target.addEvent(event)
        
        self.write_yaml()