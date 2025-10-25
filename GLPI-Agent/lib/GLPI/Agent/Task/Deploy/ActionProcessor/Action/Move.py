"""
GLPI Agent Task Deploy ActionProcessor Action Move Module

File/directory move action for deployment tasks.
"""

import os
import shutil
import glob
from typing import Dict, Any, List


class Move:
    """File/directory move action"""
    
    def __init__(self, logger=None):
        """Initialize move action"""
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
        Execute the move action.
        
        Args:
            params: Action parameters including 'from' and 'to'
        
        Returns:
            Dictionary with 'status' and 'msg'
        """
        to = params.get('to')
        if not to:
            return {
                'status': False,
                'msg': ["No destination for move action"]
            }
        
        msg = []
        status = True
        sources = self.sources(params.get('from', ''))
        
        if not sources:
            self.debug2(f"Nothing to move with: {params.get('from', '')}")
        
        for from_path in sources:
            # Get absolute path on Windows
            if os.name == 'nt':
                from_path = os.path.abspath(from_path)
            
            self.debug2(f"Moving '{from_path}' to '{to}'")
            
            try:
                # Check if source exists
                if not os.path.exists(from_path):
                    msg.append(f"Source does not exist: '{from_path}'")
                    status = False
                    continue
                
                # First copy, then remove (work-around for Windows service context)
                if os.path.isdir(from_path):
                    # Move directory
                    if os.path.exists(to) and os.path.isfile(to):
                        msg.append(f"Cannot move directory to file: '{from_path}' to '{to}'")
                        status = False
                    else:
                        shutil.copytree(from_path, to, dirs_exist_ok=True)
                        shutil.rmtree(from_path)
                else:
                    # Move file
                    os.makedirs(os.path.dirname(to), exist_ok=True)
                    shutil.copy2(from_path, to)
                    os.remove(from_path)
                
            except Exception as e:
                m = f"Failed to move: '{from_path}' to '{to}'"
                msg.append(m)
                self.debug(m)
                msg.append(str(e))
                self.debug2(str(e))
                status = False
        
        return {
            'status': status,
            'msg': msg
        }
