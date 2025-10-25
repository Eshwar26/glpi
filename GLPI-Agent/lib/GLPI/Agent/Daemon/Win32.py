"""
GLPI Agent Windows Service Daemon Module

This module provides Windows service management functionality for the GLPI Agent.
It handles service registration, lifecycle management, and threading operations.
"""

import os
import sys
import time
import threading
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

try:
    import win32serviceutil
    import win32service
    import win32event
    import win32api
    import win32con
    import pywintypes
except ImportError:
    # Provide helpful error message if pywin32 is not installed
    print("ERROR: pywin32 module is required for Windows service support")
    print("Install it with: pip install pywin32")
    sys.exit(1)

from GLPI.Agent.Daemon import Daemon
from GLPI.Agent import Version
from GLPI.Agent.Logger import Logger
from GLPI.Agent.Tools import Tools
try:
    from GLPI.Agent.Tools.Win32 import (
        start_Win32_OLE_Worker,
        setupWorkerLogger,
        is64bit,
        getAgentMemorySize,
        FreeAgentMem,
        getCurrentService
    )
except ImportError:
    # Placeholder for when Win32 tools are not yet converted
    start_Win32_OLE_Worker = None
    setupWorkerLogger = None
    is64bit = None
    getAgentMemorySize = None
    FreeAgentMem = None
    getCurrentService = None


# Service constants (in microseconds)
SERVICE_USLEEP_TIME = 200000  # 200ms in microseconds

# Convert to seconds for Python's time.sleep()
SERVICE_SLEEP_TIME = SERVICE_USLEEP_TIME / 1_000_000


class Win32Daemon(Daemon):
    """
    Windows Service implementation of the GLPI Agent Daemon.
    
    Handles service registration, lifecycle management, pause/resume,
    and memory optimization for Windows platforms.
    """

    @staticmethod
    def SERVICE_NAME():
        """Get the service name based on provider"""
        provider = Version.PROVIDER.lower()
        return f"{provider}-agent"

    @staticmethod
    def SERVICE_DISPLAYNAME():
        """Get the service display name"""
        provider = Version.PROVIDER
        return f"{provider} Agent"

    def __init__(self, **params):
        """
        Initialize the Windows daemon.
        
        Args:
            **params: Configuration parameters passed to parent class
        """
        super().__init__(**params)
        
        self.last_state = win32service.SERVICE_START_PENDING
        self._name = None
        self._displayname = None
        self.agent_thread = None
        self.worker_thread = None
        self.task_thread = None
        self._service_safetime = None
        self._optimization_rundate = None
        self._MaxPageFileUsage = None
        self.stop_event = threading.Event()

    def init(self, **params):
        """
        Initialize the daemon with configuration.
        
        When running as a service, the script makes a chdir to perl/bin,
        so we need to fix local targets set to "." to use the vardir folder.
        
        Args:
            **params: Initialization parameters
        """
        super().init(**params)

        # Fix local target paths when running as a service
        if hasattr(self, 'targets') and self.targets:
            for target in self.targets:
                if (hasattr(target, 'isType') and 
                    target.isType('local') and 
                    hasattr(target, 'getPath') and
                    target.getPath() == '.'):
                    if hasattr(self, 'config') and hasattr(self.config, 'vardir'):
                        target.setFullPath(self.config.vardir)

    def name(self, name: Optional[str] = None) -> str:
        """
        Get or set the service name.
        
        Args:
            name: Optional name to set
            
        Returns:
            The service name
        """
        if name is not None:
            self._name = name
        return self._name or self.SERVICE_NAME()

    def displayname(self, displayname: Optional[str] = None) -> str:
        """
        Get or set the service display name.
        
        Args:
            displayname: Optional display name to set
            
        Returns:
            The service display name
        """
        if displayname is not None:
            self._displayname = displayname
        return self._displayname or self.SERVICE_DISPLAYNAME()

    def RegisterService(self, **options) -> int:
        """
        Register the Windows service.
        
        Args:
            **options: Service registration options including:
                - program: Path to the program to run
                - libdir: Library directory path
                - name: Service name
                - displayname: Service display name
                
        Returns:
            0 on success, 1 if already registered, 2 on error
        """
        libdir = options.get('libdir') or getattr(self, 'libdir', None)
        program = options.get('program', '')
        
        # Try to compute libdir from this module file if not absolute
        if not libdir or not os.path.isabs(libdir) or not os.path.isdir(libdir):
            module_path = Path(__file__).resolve()
            libdir = str(module_path.parents[4])  # Go up 5 levels
            
        # Build command line parameters
        params = f'"{program}"'
        if libdir and os.path.isdir(libdir):
            params = f'-I"{libdir}" {params}'
        
        service_name = self.name(options.get('name'))
        display_name = self.displayname(options.get('displayname'))
        
        try:
            # Create the service
            hscm = win32service.OpenSCManager(
                None, None, win32service.SC_MANAGER_ALL_ACCESS
            )
            try:
                hs = win32service.CreateService(
                    hscm,
                    service_name,
                    display_name,
                    win32service.SERVICE_ALL_ACCESS,
                    win32service.SERVICE_WIN32_OWN_PROCESS,
                    win32service.SERVICE_AUTO_START,
                    win32service.SERVICE_ERROR_NORMAL,
                    f'"{sys.executable}" {params}',
                    None, 0, None, None, None
                )
                win32service.CloseServiceHandle(hs)
                print(f"Service '{display_name}' registered successfully")
                return 0
            finally:
                win32service.CloseServiceHandle(hscm)
                
        except pywintypes.error as e:
            error_code = e.winerror
            
            if error_code == 1073:  # ERROR_SERVICE_EXISTS
                print("Service still registered", file=sys.stderr)
                return 0
            elif error_code == 1072:  # ERROR_SERVICE_MARKED_FOR_DELETE
                print("Service marked for deletion.", file=sys.stderr)
                print("Computer must be rebooted to register the same service name", 
                      file=sys.stderr)
                return 1
            else:
                print(f"Service not registered: {error_code}: {e.strerror}", 
                      file=sys.stderr)
                return 2

    def DeleteService(self, **options) -> int:
        """
        Delete the Windows service.
        
        Args:
            **options: Options including optional service name
            
        Returns:
            0 on success, 1 if marked for deletion, 2 on error
        """
        service_name = self.name(options.get('name'))
        
        try:
            hscm = win32service.OpenSCManager(
                None, None, win32service.SC_MANAGER_ALL_ACCESS
            )
            try:
                hs = win32service.OpenService(
                    hscm, service_name, win32service.SERVICE_ALL_ACCESS
                )
                try:
                    win32service.DeleteService(hs)
                    print(f"Service '{service_name}' deleted successfully")
                    return 0
                finally:
                    win32service.CloseServiceHandle(hs)
            finally:
                win32service.CloseServiceHandle(hscm)
                
        except pywintypes.error as e:
            error_code = e.winerror
            
            if error_code == 1060:  # ERROR_SERVICE_DOES_NOT_EXIST
                print("Service not found", file=sys.stderr)
                return 0
            elif error_code == 1072:  # ERROR_SERVICE_MARKED_FOR_DELETE
                print("Service still marked for deletion. Computer must be rebooted",
                      file=sys.stderr)
                return 1
            else:
                print(f"Service not removed {error_code}: {e.strerror}",
                      file=sys.stderr)
                return 2

    def StartService(self):
        """
        Start the Windows service and manage its lifecycle.
        
        This method runs the main service loop, handling state transitions
        and responding to service control requests.
        """
        # Service initialization would be handled by the service framework
        # This is a simplified version showing the main loop structure
        
        timer = time.time()
        last_query = 0
        
        # Main service loop
        while not self.stop_event.is_set():
            # Handle different service states
            if self.last_state == win32service.SERVICE_START_PENDING:
                self._start_agent()
                self.last_state = win32service.SERVICE_RUNNING
                
            elif self.last_state == win32service.SERVICE_STOP_PENDING:
                self._stop_agent()
                break
                
            elif self.last_state == win32service.SERVICE_PAUSE_PENDING:
                if time.time() - timer >= 10:
                    if self.agent_thread and self.agent_thread.is_alive():
                        # Pause the agent
                        pass
                    else:
                        self.last_state = win32service.SERVICE_STOP_PENDING
                    timer = time.time()
                    
                # Check if all targets are paused
                targets = self.getTargets() if hasattr(self, 'getTargets') else []
                if all(hasattr(t, 'paused') and t.paused() for t in targets):
                    self.last_state = win32service.SERVICE_PAUSED
                    self.ApplyServiceOptimizations()
                else:
                    self.last_state = win32service.SERVICE_PAUSE_PENDING
                    
            elif self.last_state == win32service.SERVICE_CONTINUE_PENDING:
                if time.time() - timer >= 10:
                    if self.agent_thread and self.agent_thread.is_alive():
                        # Continue the agent
                        pass
                    else:
                        self.last_state = win32service.SERVICE_STOP_PENDING
                    timer = time.time()
                    
                targets = self.getTargets() if hasattr(self, 'getTargets') else []
                if not any(hasattr(t, 'paused') and t.paused() for t in targets):
                    self.last_state = win32service.SERVICE_RUNNING
                else:
                    self.last_state = win32service.SERVICE_CONTINUE_PENDING
                    
            elif self.last_state == win32service.SERVICE_PAUSED:
                if self.agent_thread and self.agent_thread.is_alive():
                    self.last_state = win32service.SERVICE_PAUSED
                else:
                    self.last_state = win32service.SERVICE_STOP_PENDING
                    
            elif self.last_state == win32service.SERVICE_RUNNING:
                if self.agent_thread and self.agent_thread.is_alive():
                    self.last_state = win32service.SERVICE_RUNNING
                else:
                    self.last_state = win32service.SERVICE_STOP_PENDING
            
            # Update service status periodically
            if time.time() - timer >= 10:
                timer = time.time()
            
            time.sleep(SERVICE_SLEEP_TIME)

    def AcceptedControls(self, controls: Optional[int] = None):
        """
        Set the accepted service control codes.
        
        Args:
            controls: Control codes to accept, defaults to STOP, SHUTDOWN, PAUSE_CONTINUE
        """
        if controls is None:
            controls = (
                win32service.SERVICE_ACCEPT_STOP |
                win32service.SERVICE_ACCEPT_SHUTDOWN |
                win32service.SERVICE_ACCEPT_PAUSE_CONTINUE
            )
        
        # This would be set in the actual service control handler
        self._accepted_controls = controls

    def _retrieveServiceName(self):
        """Retrieve and set the service name from the current running service."""
        if getCurrentService is not None:
            service = getCurrentService()
            if service:
                self.name(service.get('Name'))
                self.displayname(service.get('DisplayName'))

    def _start_agent(self):
        """Start the agent in a dedicated thread."""
        if self.agent_thread is None:
            def agent_runner():
                """Agent thread main function."""
                # Start Win32::OLE worker thread
                if start_Win32_OLE_Worker is not None:
                    self.worker_thread = start_Win32_OLE_Worker()
                
                # Set service name after worker thread has started
                self._retrieveServiceName()
                
                # Set service safe time (restart after one day if needed)
                self._service_safetime = time.time() + 86400
                
                # Initialize with service mode
                self.init(options={'service': True})
                
                # Run the agent
                if hasattr(self, 'run'):
                    self.run()
            
            self.agent_thread = threading.Thread(target=agent_runner, daemon=True)
            self.agent_thread.start()

    def _stop_agent(self):
        """Stop the agent thread gracefully."""
        timer = time.time() - 1
        tries = 10
        
        while self.agent_thread:
            if self.agent_thread.is_alive() and time.time() - timer >= 1:
                # Request thread to stop
                self.stop_event.set()
                
                if not tries:
                    # Force stop if thread doesn't respond
                    break
                    
                tries -= 1
                timer = time.time()
                
            elif not self.agent_thread.is_alive():
                self.agent_thread.join(timeout=1)
                break
                
            time.sleep(SERVICE_SLEEP_TIME)
        
        self.agent_thread = None

    def Pause(self):
        """Pause the agent service."""
        # Abort task thread if running
        if self.task_thread and self.task_thread.is_alive():
            # Signal thread to stop
            self.stop_event.set()
            self.task_thread = None
        
        # Pause all targets
        if hasattr(self, 'getTargets'):
            for target in self.getTargets():
                if hasattr(target, 'pause'):
                    target.pause()
        
        if hasattr(self, 'setStatus'):
            self.setStatus('paused')
        
        # Don't allow service restart when paused
        self._service_safetime = None
        
        if hasattr(self, 'logger') and self.logger:
            self.logger.info(f"{Version.PROVIDER} Agent paused")

    def Continue(self):
        """Resume the agent service from paused state."""
        if hasattr(self, 'setStatus'):
            self.setStatus('waiting')
        
        # Continue all targets
        if hasattr(self, 'getTargets'):
            for target in self.getTargets():
                if hasattr(target, 'continue_'):
                    target.continue_()
                elif hasattr(target, 'continue'):
                    target.__dict__.get('continue', lambda: None)()
        
        # Re-enable service restart after one day
        self._service_safetime = time.time() + 86400
        
        if hasattr(self, 'logger') and self.logger:
            self.logger.info(f"{Version.PROVIDER} Agent resumed")

    def ApplyServiceOptimizations(self):
        """Apply service-specific optimizations."""
        # Setup worker logger after service logger
        if setupWorkerLogger is not None and hasattr(self, 'config'):
            setupWorkerLogger(config=self.config)
        
        super().ApplyServiceOptimizations()
        
        # Windows-specific optimizations
        
        # Preload is64bit result to avoid multiple WMI calls
        if is64bit is not None:
            is64bit()
        
        # Also call running service optimization to free memory
        self.RunningServiceOptimization()

    def RunningServiceOptimization(self):
        """Optimize memory usage while service is running."""
        # Don't run too frequently
        if (self._optimization_rundate and 
            time.time() < self._optimization_rundate):
            return
        
        # Log memory usage before optimization
        if (hasattr(self, 'logger') and self.logger and 
            hasattr(self.logger, 'debug_level') and 
            self.logger.debug_level() and
            getAgentMemorySize is not None):
            
            working_set_size, page_file_usage = getAgentMemorySize()
            if working_set_size >= 0:
                self.logger.debug(
                    f"Agent memory usage before freeing memory: "
                    f"WSS={working_set_size} PFU={page_file_usage}"
                )
        
        # Free memory
        if FreeAgentMem is not None:
            FreeAgentMem()
        
        # Log memory usage after optimization
        if getAgentMemorySize is not None:
            working_set_size, page_file_usage = getAgentMemorySize()
            
            if hasattr(self, 'logger') and self.logger and working_set_size > 0:
                self.logger.info(
                    f"{Version.PROVIDER} Agent memory usage: "
                    f"WSS={working_set_size} PFU={page_file_usage}"
                )
            
            # Initialize max page file usage on first run
            if self._MaxPageFileUsage is None:
                self._MaxPageFileUsage = 2 * page_file_usage
            
            # Check if it's time to restart the service
            if (self._service_safetime and 
                page_file_usage > self._MaxPageFileUsage and 
                time.time() > self._service_safetime):
                
                self._service_safetime += 3600  # Delay next restart by 1 hour
                
                if hasattr(self, 'logger') and self.logger:
                    self.logger.info(
                        f"Restarting myself as {self.displayname()} service"
                    )
                
                # Restart the service
                restart_cmd = (
                    f'net stop {self.name()} && net start {self.name()}'
                )
                subprocess.Popen(
                    restart_cmd,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
        
        # Don't run optimization again for at least 60 seconds
        self._optimization_rundate = time.time() + 60

    def terminate(self):
        """Terminate the daemon and cleanup resources."""
        # Abort task thread if running
        if self.task_thread and self.task_thread.is_alive():
            self.stop_event.set()
            self.task_thread = None
        
        # Abort Win32::OLE worker thread if running
        if self.worker_thread and hasattr(self.worker_thread, 'is_alive'):
            if self.worker_thread.is_alive():
                # Signal worker to stop
                self.worker_thread = None
        
        super().terminate()

    def runTask(self, target, name: str, response=None):
        """
        Run a task in a dedicated thread (service mode).
        
        Args:
            target: Target configuration
            name: Task name
            response: Optional response object
        """
        if hasattr(self, 'setStatus'):
            self.setStatus(f"running task {name}")
        
        # Reset stop event for this task
        task_stop_event = threading.Event()
        
        def task_runner():
            """Task thread main function."""
            # We don't handle HTTPD interface in this thread
            if hasattr(self, 'server'):
                delattr(self, 'server')
            
            thread_id = threading.get_ident()
            
            if hasattr(self, 'logger') and self.logger:
                self.logger.debug(f"new thread {thread_id} to handle task {name}")
            
            # Run the actual task
            if hasattr(self, 'runTaskReal'):
                self.runTaskReal(target, name, response)
        
        self.task_thread = threading.Thread(target=task_runner, daemon=True)
        self.task_thread.start()
        
        # Wait for task to complete
        while self.task_thread:
            if not self.task_thread.is_alive():
                self.task_thread.join(timeout=1)
                self.task_thread = None
            else:
                if hasattr(self, 'sleep'):
                    self.sleep(1)
                else:
                    time.sleep(1)

