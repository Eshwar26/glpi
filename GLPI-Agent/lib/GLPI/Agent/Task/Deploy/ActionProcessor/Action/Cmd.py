"""
GLPI Agent Task Deploy ActionProcessor Action Cmd Module

Command execution action for deployment tasks.
"""

import os
import subprocess
import platform
import re
from typing import Dict, Any, List, Tuple, Optional


class Cmd:
    """Command execution action"""
    
    def __init__(self, logger=None):
        """Initialize command action"""
        self.logger = logger
    
    def debug(self, msg: str) -> None:
        """Log debug message"""
        if self.logger:
            self.logger.debug(msg)
    
    def debug2(self, msg: str) -> None:
        """Log debug2 message"""
        if self.logger and hasattr(self.logger, 'debug2'):
            self.logger.debug2(msg)
    
    @staticmethod
    def _evaluate_ret(ret_checks: Optional[List[Dict]], buf: str, exit_status: int) -> Tuple[bool, str]:
        """
        Evaluate return conditions.
        
        Args:
            ret_checks: List of return check conditions
            buf: Command output buffer
            exit_status: Exit status code
        
        Returns:
            Tuple of (success, message)
        """
        if not isinstance(ret_checks, list):
            return True, 'ok, no check to evaluate.'
        
        for ret_check in ret_checks:
            check_type = ret_check.get('type')
            values = ret_check.get('values', [])
            
            if check_type == 'okCode':
                for value in values:
                    if exit_status == int(value):
                        return True, f"ok, got expected exit status: {value}"
                return False, f"not expected exit status: {exit_status}"
            
            elif check_type == 'okPattern':
                for value in values:
                    if not value:
                        continue
                    if re.search(value, buf):
                        return True, f"ok, pattern found in log: /{value}/"
                return False, "expected pattern not found in log"
            
            elif check_type == 'errorCode':
                for value in values:
                    if exit_status == int(value):
                        return False, f"found unwanted exit status: {exit_status}"
                return True, f"ok, not an unwanted exit status: {exit_status}"
            
            elif check_type == 'errorPattern':
                for value in values:
                    if not value:
                        continue
                    if re.search(value, buf):
                        return False, f"error pattern found in log: /{value}/"
                return True, "ok, error pattern not found in log"
        
        return True, "nothing to check"
    
    def _run_on_unix(self, params: Dict[str, Any]) -> Tuple[str, str, int]:
        """
        Run command on Unix-like systems.
        
        Args:
            params: Command parameters
        
        Returns:
            Tuple of (output_buffer, error_message, exit_status)
        """
        try:
            result = subprocess.run(
                params['exec'],
                shell=True,
                capture_output=True,
                text=True
            )
            
            buf = result.stdout + result.stderr
            err_msg = ""
            exit_status = result.returncode
            
            self.debug2(f"Run: {buf}")
            
            return buf, err_msg, exit_status
            
        except Exception as e:
            return "", str(e), 127
    
    def _run_on_windows(self, params: Dict[str, Any]) -> Tuple[str, str, int]:
        """
        Run command on Windows.
        
        Args:
            params: Command parameters
        
        Returns:
            Tuple of (output_buffer, error_message, exit_status)
        """
        try:
            result = subprocess.run(
                params['exec'],
                shell=True,
                capture_output=True,
                text=True,
                timeout=params.get('timeout')
            )
            
            buf = result.stdout + result.stderr
            
            if not buf:
                self.debug2("Run: Got no output")
            else:
                self.debug2(f"Run: {buf}")
            
            err_msg = ""
            exit_code = result.returncode
            
            return buf, err_msg, exit_code
            
        except subprocess.TimeoutExpired:
            return "", "timeout", 293
        except Exception as e:
            return "", str(e), 50  # ERROR_NOT_SUPPORTED
    
    def do(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the command action.
        
        Args:
            params: Action parameters including 'exec', 'envs', 'retChecks', 'logLineLimit'
        
        Returns:
            Dictionary with 'status' and 'msg'
        """
        if 'exec' not in params:
            return {
                'status': False,
                'msg': ["Internal agent error"]
            }
        
        # Save and set environment variables
        envs_saved = {}
        if params.get('envs'):
            for key, value in params['envs'].items():
                envs_saved[key] = os.environ.get(key)
                os.environ[key] = value
        
        # Run command based on platform
        if platform.system() == 'Windows':
            buf, err_msg, exit_status = self._run_on_windows(params)
        else:
            buf, err_msg, exit_status = self._run_on_unix(params)
        
        # Process output with line limit
        log_line_limit = params.get('logLineLimit', 10)
        
        msg = []
        if buf:
            lines = buf.split('\n')
            for line in reversed(lines):
                line = line.rstrip()
                msg.insert(0, line)
                # Empty lines are kept but don't count against limit
                if line and log_line_limit > 0:
                    log_line_limit -= 1
                    if log_line_limit <= 0:
                        break
        
        # Evaluate return checks
        status, ret_msg = self._evaluate_ret(params.get('retChecks'), buf, exit_status)
        
        # Build final message
        msg.append("--------------------------------")
        if err_msg:
            msg.append(f"error msg: `{err_msg}'")
        msg.append(f"exit status: `{exit_status}'")
        msg.append(ret_msg)
        
        # Add header
        msg.insert(0, "================================")
        msg.insert(0, f"Started cmd: {params['exec']}")
        msg.insert(0, "================================")
        
        # Log messages
        for line in msg:
            self.debug(line)
        self.debug(f"final status: {status}")
        
        # Restore environment variables
        for key, value in envs_saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        
        return {
            'status': status,
            'msg': msg
        }
