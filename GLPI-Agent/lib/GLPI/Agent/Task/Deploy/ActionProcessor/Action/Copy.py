"""
GLPI Agent Task Deploy ActionProcessor Action Copy Module

File/directory copy action for deployment tasks.
"""

import os
import shutil
import glob
from typing import Dict, Any, List


class Copy:
    """File/directory copy action"""
    
    def __init__(self, logger=None):
        """Initialize copy action"""
        self.logger = logger
    
    def debug(self, msg: str) -> None:
        """Log debug message"""
        if self.logger:
            self.logger.debug(msg)
    
    def debug2(self, msg: str) -> None:
        """Log debug2 message"""
        if self.logger and hasattr(self.logger, 'debug2'):
            self.logger.debug2(msg)
    
    def sources(self, from_pattern: str) -> List[str]:
        """
        Resolve source paths using glob pattern.
        
        Args:
            from_pattern: Source path or pattern
        
        Returns:
            List of resolved source paths
        """
        if not from_pattern:
            return []
        
        # Expand glob pattern
        sources = glob.glob(from_pattern)
        return sources if sources else []
    
    def do(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the copy action.
        
        Args:
            params: Action parameters including 'from' and 'to'
        
        Returns:
            Dictionary with 'status' and 'msg'
        """
        to = params.get('to')
        if not to:
            return {
                'status': False,
                'msg': ["No destination for copy action"]
            }
        
        msg = []
        status = True
        sources = self.sources(params.get('from', ''))
        
        if not sources:
            self.debug2(f"Nothing to copy with: {params.get('from', '')}")
        
        for from_path in sources:
            # Get absolute path on Windows
            if os.name == 'nt':
                from_path = os.path.abspath(from_path)
            
            self.debug2(f"Copying '{from_path}' to '{to}'")
            
            try:
                # Check if source exists
                if not os.path.exists(from_path):
                    msg.append(f"Source does not exist: '{from_path}'")
                    status = False
                    continue
                
                # Copy file or directory
                if os.path.isdir(from_path):
                    # Copy directory recursively
                    if os.path.exists(to) and os.path.isfile(to):
                        msg.append(f"Cannot copy directory to file: '{from_path}' to '{to}'")
                        status = False
                    else:
                        shutil.copytree(from_path, to, dirs_exist_ok=True)
                else:
                    # Copy file
                    os.makedirs(os.path.dirname(to), exist_ok=True)
                    shutil.copy2(from_path, to)
                
            except Exception as e:
                m = f"Failed to copy: '{from_path}' to '{to}'"
                msg.append(m)
                self.debug(m)
                msg.append(str(e))
                self.debug2(str(e))
                status = False
        
        return {
            'status': status,
            'msg': msg
        }
