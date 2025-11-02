#!/usr/bin/env python3
"""CustomCodeSigning - Code signing step for Windows packaging"""

import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

BASH = r'C:\Program Files\Git\bin\bash.exe'
SSH = "ssh -T -o StrictHostKeyChecking=yes -i private.key codesign codesign"


class CustomCodeSigning:
    """Code signing step for Windows build system"""
    
    def __init__(self, boss, config, global_config):
        """
        Initialize code signing step.
        
        Args:
            boss: Build system boss object
            config: Step configuration
            global_config: Global build configuration
        """
        self.boss = boss
        self.config = config
        self.global_config = global_config
    
    def _resolve_file(self, file: str) -> str:
        """
        Resolve file path with variable substitution.
        
        Args:
            file: File path with optional variable placeholders
            
        Returns:
            Resolved file path
        """
        file = file.replace('<image_dir>', self.global_config.get('image_dir', ''))
        file = file.replace('<output_dir>', self.global_config.get('output_dir', ''))
        file = file.replace('<output_basename>', self.global_config.get('output_basename', ''))
        return file
    
    def run(self) -> int:
        """
        Run code signing step.
        
        Returns:
            0 on success, 1 on failure
        """
        if not self.global_config.get('codesigning'):
            self.boss.message(2, "* skipping as code signing is not enabled")
            return 0
        
        if not os.path.exists("private.key"):
            self.boss.message(2, "* skipping as code signing is not setup")
            return 0
        
        files_list = self.config.get('files', [])
        dlls_list = self.config.get('dlls', [])
        
        if not files_list and not dlls_list:
            self.boss.message(2, "* skipping as no file configured for code signing")
            return 0
        
        files = list(files_list) if files_list else []
        dlls_folders = list(dlls_list) if dlls_list else []
        
        # Search for DLLs in folders
        while dlls_folders:
            path = dlls_folders.pop(0)
            folder = self._resolve_file(path)
            
            if not os.path.isdir(folder):
                self.boss.message(2, f" * no such '{path}' folder, skipping")
                continue
            
            for entry in os.listdir(folder):
                if entry in ('.', '..'):
                    continue
                
                fullpath = os.path.join(folder, entry)
                if os.path.isfile(fullpath) and entry.lower().endswith('.dll'):
                    files.append(os.path.join(path, entry))
                elif os.path.isdir(fullpath):
                    dlls_folders.append(os.path.join(path, entry))
        
        expected = len(files)
        
        if self.config.get('dlls') and expected > 1:
            self.boss.message(2, f" * having {expected} files to sign")
        
        count = 0
        for file in files:
            if isinstance(file, dict):
                path = file.get('filename', '')
            else:
                path = file
            
            installed_file = self._resolve_file(path)
            
            if not os.path.exists(installed_file):
                self.boss.message(2, f" * no such '{path}' file, skipping")
                continue
            
            if isinstance(file, dict):
                name = self._resolve_file(file.get('name', ''))
            else:
                name = file
            
            # Remove variable placeholders from name
            import re
            name = re.sub(r'<[^>]+>/', '', name)
            
            # Create signed file path
            if '.' in installed_file:
                base, ext = installed_file.rsplit('.', 1)
                signed_file = f"{base}-signed.{ext}"
            else:
                signed_file = f"{installed_file}-signed"
            
            command = f"cat '{installed_file}' | {SSH} '{name}' > '{signed_file}'"
            signed = False
            
            try:
                result = subprocess.run([BASH, "-c", command], check=False)
                if result.returncode == 0 and os.path.exists(signed_file) and os.path.getsize(signed_file) > 0:
                    try:
                        os.unlink(installed_file)
                    except OSError:
                        self.boss.message(2, f" * {path}: failed to delete '{installed_file}'")
                    
                    try:
                        os.rename(signed_file, installed_file)
                        self.boss.message(1, f" * signed '{path}'")
                        count += 1
                        signed = True
                    except OSError:
                        self.boss.message(2, f" * {path}: failed to replace '{installed_file}' by '{signed_file}' signed version")
            except Exception as e:
                self.boss.message(2, f" * Error signing {path}: {e}")
            
            if not signed:
                abort_msg = ", aborting..." if expected > 1 and count < expected else ""
                self.boss.message(1, f" * failed to signed '{path}'{abort_msg}")
                break
        
        self.boss.message(1, f" * {count} file{'s' if count != 1 else ''} signed")
        
        return 0 if count == expected else 1

