#!/usr/bin/env python3
"""
GLPI Agent Event - Python Implementation

Event management for triggering and scheduling agent tasks.
Supports various event types: init, runnow, taskrun, partial, maintenance, and job.
"""

import re
from typing import Any, Dict, Optional


class Event:
    """
    Event object for GLPI Agent task scheduling and triggering.
    
    Supports multiple event types:
    - init: Service startup events
    - runnow: Immediate task execution requests
    - taskrun: Scheduled task execution
    - partial: Partial inventory requests
    - maintenance: Internal maintenance tasks
    - job: Toolbox-managed inventory tasks
    """
    
    def __init__(self, **params: Any):
        """
        Initialize event from parameters.
        
        Args:
            **params: Event parameters including:
                - init: Init event flag
                - runnow: Run now flag
                - taskrun: Task run flag
                - partial: Partial inventory flag
                - maintenance: Maintenance flag
                - job: Job event flag
                - task/tasks: Task name(s)
                - delay: Delay in seconds
                - category: Inventory category
                - target: Target identifier
                - rundate: Scheduled run timestamp
                - name: Event name
                - full: Full inventory flag
                - reschedule: Reschedule flag
        """
        # Initialize from message content if provided
        if params.get('from_message'):
            params = params['from_message']
        
        self._init = 0
        self._runnow = 0
        self._taskrun = 0
        self._partial = 0
        self._maintenance = 0
        self._job = 0
        self._name = ''
        self._task = ''
        self._category = ''
        self._target = ''
        self._delay = 0
        self._rundate = 0
        self._httpd = 0
        self._params = {}
        
        # Determine event type and configure accordingly
        if self._matches_bool(params.get('init')):
            # Init event (service startup)
            self._init = 1
            self._task = params.get('task', '')
            self._name = 'init'
            self._rundate = params.get('rundate', 0)
            self._httpd = 0
        
        elif self._matches_bool(params.get('runnow')):
            # Run now event (immediate execution)
            self._runnow = 1
            self._name = 'run now'
            self._task = params.get('task') or params.get('tasks') or 'all'
            self._delay = params.get('delay', 0)
            self._httpd = 1
            
            # Store additional parameters
            excluded = {'runnow', 'task', 'tasks', 'delay'}
            self._params = {
                k: params.get(k, '')
                for k in params.keys()
                if k not in excluded
            }
        
        elif self._matches_bool(params.get('taskrun')):
            # Task run event (scheduled execution)
            self._taskrun = 1
            self._name = 'run'
            self._task = params.get('task', '')
            self._delay = params.get('delay', 0)
            self._httpd = 1
            self._params = {
                'reschedule': params.get('reschedule', 0)
            }
            
            # Handle inventory-specific parameters
            if params.get('task') == 'inventory':
                if 'full' in params:
                    self._params['full'] = 1 if self._matches_bool(params['full']) else 0
                elif 'partial' in params:
                    self._params['full'] = 0 if self._matches_bool(params['partial']) else 1
                else:
                    # Default to full inventory
                    self._params['full'] = 1
        
        elif self._matches_bool(params.get('partial')):
            # Partial inventory event
            self._partial = 1
            self._task = 'inventory'
            self._name = 'partial inventory'
            self._category = params.get('category', '')
            self._httpd = 1
            
            # Store additional parameters (for database partial inventory)
            self._params = {
                k: params.get(k, '')
                for k in params.keys()
                if k != 'partial'
            }
        
        elif self._matches_bool(params.get('maintenance')):
            # Maintenance event
            self._maintenance = 1
            self._task = params.get('task', '')
            self._name = params.get('name', 'maintenance')
            self._delay = params.get('delay', 0)
            self._httpd = 0
        
        elif params.get('name') and self._matches_bool(params.get('job')):
            # Job event (toolbox-managed)
            self._job = 1
            self._name = params['name']
            self._rundate = params.get('rundate', 0)
            self._task = params.get('task', 'unknown')
            self._httpd = 0
        
        # Set target if provided
        if 'target' in params:
            self._target = params['target']
    
    @staticmethod
    def _matches_bool(value: Any) -> bool:
        """
        Check if value matches boolean pattern (yes/1/true).
        
        Args:
            value: Value to check
            
        Returns:
            True if value indicates boolean true
        """
        if value is None:
            return False
        
        if isinstance(value, bool):
            return value
        
        if isinstance(value, int):
            return value == 1
        
        if isinstance(value, str):
            return re.match(r'^(yes|1|true)$', value, re.IGNORECASE) is not None
        
        return False
    
    # Event name (mandatory)
    def name(self) -> str:
        """Get event name."""
        return self._name or ''
    
    # Event types
    def init(self) -> int:
        """Check if this is an init event."""
        return self._init or 0
    
    def partial(self) -> int:
        """Check if this is a partial inventory event."""
        return self._partial or 0
    
    def maintenance(self) -> int:
        """Check if this is a maintenance event."""
        return self._maintenance or 0
    
    def job(self) -> int:
        """Check if this is a job event."""
        return self._job or 0
    
    def runnow(self) -> int:
        """Check if this is a run now event."""
        return self._runnow or 0
    
    def taskrun(self) -> int:
        """Check if this is a task run event."""
        return self._taskrun or 0
    
    # Event attributes
    def task(self) -> str:
        """Get task name."""
        return self._task or ''
    
    def category(self) -> str:
        """Get inventory category."""
        return self._category or ''
    
    def target(self) -> str:
        """Get target identifier."""
        return self._target or ''
    
    def params(self) -> Dict[str, Any]:
        """Get event parameters dictionary."""
        return self._params or {}
    
    def get(self, key: str) -> Any:
        """
        Get specific parameter value.
        
        Args:
            key: Parameter key
            
        Returns:
            Parameter value or None
        """
        if not key or not isinstance(self._params, dict):
            return None
        return self._params.get(key)
    
    def delay(self) -> int:
        """Get event delay in seconds."""
        return self._delay or 0
    
    def rundate(self, rundate: Optional[int] = None) -> int:
        """
        Get or set event run date.
        
        Args:
            rundate: Optional run timestamp to set
            
        Returns:
            Run date timestamp
        """
        if rundate is not None:
            self._rundate = rundate
        return self._rundate or 0
    
    def httpd_support(self) -> int:
        """Check if event supports HTTP triggering."""
        return self._httpd or 0
    
    def dump_as_string(self) -> str:
        """
        Dump event as query string.
        
        Returns:
            Event parameters as query string (key=value&...)
        """
        dump = self.dump_for_message()
        parts = []
        
        for key, value in dump.items():
            if not isinstance(value, (dict, list)):
                parts.append(f"{key}={value}")
        
        return '&'.join(parts)
    
    def dump_for_message(self) -> Dict[str, Any]:
        """
        Dump event data for message serialization.
        
        Returns:
            Dictionary of event attributes
        """
        dump = {}
        
        for key, value in self.__dict__.items():
            # Remove leading underscore from attribute names
            clean_key = key.lstrip('_')
            dump[clean_key] = value if value is not None else ''
        
        return dump
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        event_type = (
            'init' if self._init else
            'runnow' if self._runnow else
            'taskrun' if self._taskrun else
            'partial' if self._partial else
            'maintenance' if self._maintenance else
            'job' if self._job else
            'unknown'
        )
        return f"Event(type={event_type}, name='{self._name}', task='{self._task}')"


if __name__ == "__main__":
    # Test various event types
    print("=== GLPI Agent Event Tests ===\n")
    
    # Test init event
    init_event = Event(init='yes', task='inventory', rundate=1234567890)
    print(f"Init Event: {init_event}")
    print(f"  - name: {init_event.name()}")
    print(f"  - is init: {init_event.init()}")
    print(f"  - task: {init_event.task()}")
    print(f"  - rundate: {init_event.rundate()}")
    print()
    
    # Test runnow event
    runnow_event = Event(runnow='1', task='inventory', delay=30, full='yes')
    print(f"Run Now Event: {runnow_event}")
    print(f"  - name: {runnow_event.name()}")
    print(f"  - is runnow: {runnow_event.runnow()}")
    print(f"  - task: {runnow_event.task()}")
    print(f"  - delay: {runnow_event.delay()}")
    print(f"  - dump: {runnow_event.dump_as_string()}")
    print()
    
    # Test partial event
    partial_event = Event(partial='yes', category='hardware,network')
    print(f"Partial Event: {partial_event}")
    print(f"  - name: {partial_event.name()}")
    print(f"  - is partial: {partial_event.partial()}")
    print(f"  - task: {partial_event.task()}")
    print(f"  - category: {partial_event.category()}")
    print()
    
    # Test taskrun event
    taskrun_event = Event(taskrun='1', task='inventory', full='1', reschedule='1')
    print(f"Task Run Event: {taskrun_event}")
    print(f"  - name: {taskrun_event.name()}")
    print(f"  - is taskrun: {taskrun_event.taskrun()}")
    print(f"  - task: {taskrun_event.task()}")
    print(f"  - full param: {taskrun_event.get('full')}")
    print(f"  - reschedule: {taskrun_event.get('reschedule')}")
    print()
    
    # Test maintenance event
    maint_event = Event(maintenance='yes', task='deploy', name='cleanup', delay=60)
    print(f"Maintenance Event: {maint_event}")
    print(f"  - name: {maint_event.name()}")
    print(f"  - is maintenance: {maint_event.maintenance()}")
    print(f"  - task: {maint_event.task()}")
    print(f"  - delay: {maint_event.delay()}")
    print()
    
    # Test job event
    job_event = Event(job='1', name='scheduled-inventory', task='inventory', rundate=1700000000)
    print(f"Job Event: {job_event}")
    print(f"  - name: {job_event.name()}")
    print(f"  - is job: {job_event.job()}")
    print(f"  - task: {job_event.task()}")
    print(f"  - rundate: {job_event.rundate()}")