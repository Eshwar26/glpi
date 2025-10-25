from typing import List, Dict, Any, Optional, TYPE_CHECKING

from ....logger import Logger
from .usercheck import UserCheck
from .checkprocessor import CheckProcessor

if TYPE_CHECKING:
    from .file import File
    from ....http.fusion_client import FusionClient


class Job:
    def __init__(self, **params):
        data = params.get('data', {})
        
        self._remoteUrl = params.get('remoteUrl')
        self._client = params.get('client')
        self._machineid = params.get('machineid')
        self._currentStep = 'init'
        
        self.logger = params.get('logger') or Logger()
        self.uuid = data.get('uuid')
        self.requires = data.get('requires', {})
        self.checks = data.get('checks', [])
        self.userchecks = data.get('userinteractions', [])
        self.actions = data.get('actions', [])
        self.associatedFiles = params.get('associatedFiles', [])
    
    def getNextToProcess(self) -> Optional[Dict[str, Any]]:
        """Get next action to process"""
        if not self.actions:
            return None
        return self.actions.pop(0) if self.actions else None
    
    def currentStep(self, step: str) -> str:
        """Set current processing step"""
        self._currentStep = '' if step == 'end' else step
        return self._currentStep
    
    def requiresSoftwaresInventory(self) -> bool:
        """Check if job requires software inventory"""
        return (isinstance(self.requires, dict) and 
                self.requires.get('softwares-inventory', False))
    
    def setStatus(self, **params):
        """Send status update to server"""
        if not self._remoteUrl:
            return
        
        # Base action hash to send to server
        action = {
            'action': 'setStatus',
            'machineid': self._machineid,
            'part': 'job',
            'uuid': self.uuid,
        }
        
        # Handle file-specific status
        if 'file' in params and params['file']:
            action['part'] = 'file'
            action['sha512'] = params['file'].sha512
        
        # Map optional parameters
        for key in ['status', 'actionnum', 'checknum', 'msg']:
            if key in params and params[key] is not None:
                action[key] = params[key]
        
        # Include current step if defined
        if self._currentStep:
            action['currentStep'] = self._currentStep
        
        # Send status to server
        if self._client:
            self._client.send(url=self._remoteUrl, args=action)
    
    def skip_on_check_failure(self, **params) -> bool:
        """Process checks and return True if job should be skipped"""
        logger = self.logger
        checks = params.get('checks', self.checks)
        level = params.get('level', 'job')
        
        if not isinstance(checks, list):
            return False
        
        # Make a copy to avoid modifying original
        checks_copy = list(checks)
        checknum = 0
        
        while checks_copy:
            checknum += 1
            check_data = checks_copy.pop(0)
            
            if not check_data:
                continue
            
            check_type = check_data.get('type', 'unsupported')
            
            # Create check processor
            check = CheckProcessor(
                check=check_data,
                logger=logger
            )
            
            name = check.name()
            check_status = check.process()
            
            if check_status in ('abort', 'error', 'ko', 'skip', 'startnow'):
                if logger:
                    logger.info(f"Skipping {level} because {name} check #{checknum} failed")
                
                if check.is_type('skip'):
                    self.setStatus(
                        status='ok',
                        msg=f"check #{checknum}, {name} not successful then skip {level}",
                        checknum=checknum-1
                    )
                    self.setStatus(
                        status='ok',
                        msg=f"{level} skipped"
                    )
                    
                elif check.is_type('startnow'):
                    self.setStatus(
                        status='ok',
                        msg=f"check #{checknum}, {name} not successful then start {level} now",
                        checknum=checknum-1
                    )
                    self.setStatus(
                        status='ok',
                        msg=f"{level} started now"
                    )
                    # Shortcut other checks - job is not to be skipped
                    return False
                    
                else:
                    self.setStatus(
                        status='ko',
                        msg=f"check #{checknum}, failure on {name}, {check.message()}",
                        checknum=checknum-1
                    )
                
                return True
            
            # Log successful check
            info = f"{check.is_type()}, {check.message()}"
            if logger:
                logger.debug(f"check #{checknum}: {name}, got {check_status}, {info}")
            
            if (check.is_type() in ('warning', 'info')) and check_status != 'ok':
                self.setStatus(
                    status=check_status,
                    msg=f"check #{checknum}, {name} {info}",
                    checknum=checknum-1
                )
            else:
                self.setStatus(
                    status=check_status,
                    msg=f"check #{checknum}, {name} passed",
                    checknum=checknum-1
                )
        
        return False
    
    def next_on_usercheck(self, **params) -> bool:
        """Process user interaction checks"""
        logger = self.logger
        checks = params.get('userchecks', self.userchecks)
        check_type = params.get('type', 'after')
        
        if not checks:
            return False
        
        if not isinstance(checks, list):
            if logger:
                logger.debug(f"usercheck {check_type}: unexpected usercheck request")
            return False
        
        # Filter checks by type
        filtered_checks = [
            check for check in checks 
            if check.get('type') == check_type
        ]
        
        if not filtered_checks:
            if logger:
                logger.debug2(f"usercheck {check_type}: no user interaction requested")
            return False
        
        while filtered_checks:
            check_data = filtered_checks.pop(0)
            
            check = UserCheck(
                check=check_data,
                logger=logger
            )
            
            if not check:
                continue
            
            # Warning: Agent may wait here for user response
            check.tell_users()
            
            # Report collected user events to server
            for event in check.getEvents():
                self.setUserEvent(event)
            
            if check.stopped():
                return True
        
        return False
    
    def setUserEvent(self, userevent: Dict[str, Any]):
        """Send user event to server"""
        if not self._remoteUrl:
            return
        
        # Base user event action
        action = {
            'action': 'setUserEvent',
            'machineid': self._machineid,
            'part': 'job',
            'uuid': self.uuid,
        }
        
        # Map user event parameters
        for key in ['type', 'behavior', 'event', 'user']:
            if key in userevent and userevent[key] is not None:
                action[key] = userevent[key]
        
        # Include current step if defined
        if self._currentStep:
            action['currentStep'] = self._currentStep
        
        # Send to server
        if self._client:
            self._client.send(url=self._remoteUrl, args=action)