import os
from typing import Dict, Any, Optional

from ....logger import Logger
from .action import Action


class ActionProcessor:
    def __init__(self, **params):
        if not params.get('workdir'):
            raise ValueError("no workdir parameter")
        
        self._logger = params.get('logger') or Logger()
        self._workdir = params['workdir']
        self._curdir = os.getcwd()
        self._failed = False
    
    def starting(self):
        """Change to work directory"""
        if self._workdir:
            os.chdir(self._workdir)
    
    def done(self):
        """Return to original directory"""
        if self._curdir:
            os.chdir(self._curdir)
    
    def failure(self):
        """Mark processor as failed"""
        self._failed = True
    
    def failed(self) -> bool:
        """Check if processor has failed"""
        return self._failed
    
    def process(self, action_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Process an action with given parameters"""
        if action_name == 'checks':
            # Not an action - skip
            return {'status': True, 'msg': []}
        
        # Handle supported actions
        if action_name.lower() in ('cmd', 'copy', 'delete', 'mkdir', 'move'):
            self._logger.debug2(f"Processing {action_name} action...")
            
            action = Action(
                logger=self._logger,
                action=action_name
            )
            
            return action.do(params)
        
        else:
            self._logger.debug(f"Unknown action type: '{action_name}'")
            return {
                'status': False,
                'msg': [f"unknown action `{action_name}`"]
            }