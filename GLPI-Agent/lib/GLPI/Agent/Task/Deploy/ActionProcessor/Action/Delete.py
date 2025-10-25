"""
GLPI Agent Task Deploy ActionProcessor Action Delete Module

File/directory deletion action for deployment tasks.
"""

import os
import shutil
from typing import Dict, Any, List


class Delete:
    """File/directory deletion action"""
    
    def __init__(self, logger=None):
        """Initialize delete action"""
        self.logger = logger
    
    def debug(self, msg: str) -> None:
        """Log debug message"""
        if self.logger:
            self.logger.debug(msg)
    
    def debug2(self, msg: str) -> None:
        """Log debug2 message"""
        if self.logger and hasattr(self.logger, 'debug2'):
            self.logger.debug2(msg)
    
    def do(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the delete action.
        
        Args:
            params: Action parameters including 'list' of paths to delete
        
        Returns:
            Dictionary with 'status' and 'msg'
        """
        delete_list = params.get('list', [])
        
        if not delete_list:
            return {
                'status': False,
                'msg': ["No folder to delete"]
            }
        
        msg = []
        status = True
        
        for loc in delete_list:
            self.debug2(f"Trying to delete '{loc}'")
            
            try:
                if os.path.isfile(loc):
                    os.remove(loc)
                elif os.path.isdir(loc):
                    shutil.rmtree(loc)
                
                # Verify deletion
                if os.path.exists(loc):
                    status = False
                    m = f"Failed to delete {loc}"
                    msg.append(m)
                    self.debug(m)
                    
            except Exception as e:
                status = False
                m = f"Failed to delete {loc}: {e}"
                msg.append(m)
                self.debug(m)
        
        return {
            'status': status,
            'msg': msg
        }
