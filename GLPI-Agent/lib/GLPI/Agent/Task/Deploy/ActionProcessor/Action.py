import glob
import os
import sys
from typing import Dict, Any, List

from .....logger import Logger


class Action:
    def __init__(self, **params):
        self._logger = params.get('logger') or Logger()
        self._action_type = params.get('action', '').lower()
    
    def do(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the action - to be overridden by subclasses"""
        if self._action_type == 'cmd':
            return self._do_cmd(params)
        elif self._action_type == 'copy':
            return self._do_copy(params)
        elif self._action_type == 'delete':
            return self._do_delete(params)
        elif self._action_type == 'mkdir':
            return self._do_mkdir(params)
        elif self._action_type == 'move':
            return self._do_move(params)
        else:
            return {
                'status': False,
                'msg': [f'Unknown action type: {self._action_type}']
            }
    
    def _do_cmd(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute command action"""
        import subprocess
        
        command = params.get('exec')
        if not command:
            return {'status': False, 'msg': ['No command specified']}
        
        try:
            # Execute command
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=params.get('timeout', 300)
            )
            
            messages = []
            if result.stdout:
                messages.extend(result.stdout.strip().split('\n'))
            if result.stderr:
                messages.extend(result.stderr.strip().split('\n'))
            
            # Filter empty messages
            messages = [msg for msg in messages if msg.strip()]
            
            return {
                'status': result.returncode == 0,
                'msg': messages or [f'Command executed with return code {result.returncode}']
            }
            
        except subprocess.TimeoutExpired:
            return {'status': False, 'msg': ['Command timeout']}
        except Exception as e:
            return {'status': False, 'msg': [f'Command failed: {e}']}
    
    def _do_copy(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute copy action"""
        import shutil
        
        from_path = params.get('from')
        to_path = params.get('to')
        
        if not from_path or not to_path:
            return {'status': False, 'msg': ['Missing from or to parameter']}
        
        try:
            messages = []
            sources = self.sources(from_path)
            
            for source in sources:
                if os.path.isfile(source):
                    shutil.copy2(source, to_path)
                    messages.append(f'Copied file {source} to {to_path}')
                elif os.path.isdir(source):
                    if os.path.exists(to_path):
                        # Copy contents into existing directory
                        dest_dir = os.path.join(to_path, os.path.basename(source))
                        shutil.copytree(source, dest_dir)
                    else:
                        shutil.copytree(source, to_path)
                    messages.append(f'Copied directory {source} to {to_path}')
            
            return {
                'status': True,
                'msg': messages or ['Copy completed']
            }
            
        except Exception as e:
            return {'status': False, 'msg': [f'Copy failed: {e}']}
    
    def _do_delete(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute delete action"""
        import shutil
        
        target = params.get('list', [])
        if isinstance(target, str):
            target = [target]
        
        if not target:
            return {'status': False, 'msg': ['No files specified for deletion']}
        
        try:
            messages = []
            
            for item in target:
                sources = self.sources(item)
                
                for source in sources:
                    if os.path.isfile(source):
                        os.remove(source)
                        messages.append(f'Deleted file {source}')
                    elif os.path.isdir(source):
                        shutil.rmtree(source)
                        messages.append(f'Deleted directory {source}')
                    elif os.path.exists(source):
                        os.remove(source)
                        messages.append(f'Deleted {source}')
            
            return {
                'status': True,
                'msg': messages or ['Delete completed']
            }
            
        except Exception as e:
            return {'status': False, 'msg': [f'Delete failed: {e}']}
    
    def _do_mkdir(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute mkdir action"""
        target = params.get('list', [])
        if isinstance(target, str):
            target = [target]
        
        if not target:
            return {'status': False, 'msg': ['No directories specified']}
        
        try:
            messages = []
            
            for directory in target:
                os.makedirs(directory, exist_ok=True)
                messages.append(f'Created directory {directory}')
            
            return {
                'status': True,
                'msg': messages or ['Mkdir completed']
            }
            
        except Exception as e:
            return {'status': False, 'msg': [f'Mkdir failed: {e}']}
    
    def _do_move(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute move action"""
        import shutil
        
        from_path = params.get('from')
        to_path = params.get('to')
        
        if not from_path or not to_path:
            return {'status': False, 'msg': ['Missing from or to parameter']}
        
        try:
            messages = []
            sources = self.sources(from_path)
            
            for source in sources:
                shutil.move(source, to_path)
                messages.append(f'Moved {source} to {to_path}')
            
            return {
                'status': True,
                'msg': messages or ['Move completed']
            }
            
        except Exception as e:
            return {'status': False, 'msg': [f'Move failed: {e}']}
    
    def sources(self, from_path: str) -> List[str]:
        """Get list of source files/directories matching pattern"""
        if sys.platform.startswith('win'):
            # Windows glob handling
            import fnmatch
            if '*' in from_path or '?' in from_path:
                return glob.glob(from_path)
            else:
                return [from_path] if os.path.exists(from_path) else []
        else:
            # Unix glob handling
            return glob.glob(from_path)
    
    def debug(self, message: str):
        """Log debug message"""
        self._logger.debug(message)
    
    def debug2(self, message: str):
        """Log verbose debug message"""
        self._logger.debug2(message)