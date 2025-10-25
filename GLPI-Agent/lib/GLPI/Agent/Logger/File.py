"""
GLPI::Agent::Logger::File - A file backend for the logger

This is a file-based backend for the logger. It supports automatic filesize
limitation.
"""

import os
import time
from datetime import datetime
from pathlib import Path

from GLPI.Agent.Logger.Backend import Backend


class File(Backend):
    """File-based logger backend with automatic filesize limitation."""
    
    def __init__(self, logfile=None, logfile_maxsize=None, **params):
        """
        Initialize the file logger backend.
        
        Args:
            logfile (str): Path to the log file
            logfile_maxsize (int): Maximum log file size in MB (0 for unlimited)
            **params: Additional parameters passed to parent
        """
        super().__init__(params.get('config'))
        self.logfile = logfile
        # Convert from MB to bytes
        self.logfile_maxsize = logfile_maxsize * 1024 * 1024 if logfile_maxsize else 0
    
    def add_message(self, level, message):
        """
        Add a message to the log file.
        
        Args:
            level (str): Log level (debug, info, warning, error)
            message (str): Log message
        """
        if not self.logfile:
            return
        
        mode = 'a'  # Append mode by default
        
        # Check if we need to truncate the file due to size limit
        if self.logfile_maxsize:
            if os.path.exists(self.logfile):
                if os.path.getsize(self.logfile) > self.logfile_maxsize:
                    mode = 'w'  # Truncate mode
        
        try:
            # Open file and acquire lock
            retry_until = time.time() + 60
            locked = False
            
            while time.time() < retry_until and not locked:
                try:
                    # Open with exclusive access (Windows) or use fcntl (Unix)
                    handle = open(self.logfile, mode, encoding='utf-8')
                    
                    # Try to get an exclusive lock
                    try:
                        if os.name == 'nt':
                            # Windows file locking
                            import msvcrt
                            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                        else:
                            # Unix file locking
                            import fcntl
                            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        locked = True
                    except (IOError, OSError):
                        handle.close()
                        time.sleep(0.1)
                        continue
                    
                    if locked:
                        # Write the log message
                        timestamp = datetime.now().strftime('%a %b %d %H:%M:%S %Y')
                        handle.write(f"[{timestamp}][{level}] {message}\n")
                        handle.close()
                        break
                        
                except (IOError, OSError) as e:
                    print(f"Warning: Can't open {self.logfile}: {e}")
                    return
            
            if not locked:
                raise IOError(f"Can't get an exclusive lock on {self.logfile}")
                
        except Exception as e:
            print(f"Warning: Error writing to log file: {e}")
