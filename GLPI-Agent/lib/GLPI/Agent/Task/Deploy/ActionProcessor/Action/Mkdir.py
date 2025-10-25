"""
GLPI Agent Task Deploy ActionProcessor Action Mkdir Module

Directory creation action for deployment tasks.
"""

import os
from typing import Dict, Any, List


class Mkdir:
    """Directory creation action"""
    
    def __init__(self, logger=None):
        """Initialize mkdir action"""
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
        Execute the mkdir action.
        
        Args:
            params: Action parameters including 'list' of directories to create
        
        Returns:
            Dictionary with 'status' and 'msg'
        """
        dir_list = params.get('list', [])
        
        if not dir_list:
            return {
                'status': False,
                'msg': ["No destination folder to create"]
            }
        
        msg = []
        status = True
        
        for directory in dir_list:
            if os.path.isdir(directory):
                m = f"Directory {directory} already exists"
                msg.append(m)
                self.debug(m)
            else:
                self.debug2(f"Trying to create '{directory}'")
                
                try:
                    os.makedirs(directory, exist_ok=True)
                    
                    if not os.path.isdir(directory):
                        status = False
                        m = f"Failed to create {directory} directory"
                        msg.append(m)
                        self.debug(m)
                        
                except Exception as e:
                    status = False
                    m = f"Failed to create {directory} directory"
                    msg.append(m)
                    msg.append(str(e))
                    self.debug(m)
                    self.debug(str(e))
        
        return {
            'status': status,
            'msg': msg
        }
