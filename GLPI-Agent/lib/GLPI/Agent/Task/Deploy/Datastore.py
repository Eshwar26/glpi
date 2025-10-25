import os
import glob
import shutil
import time
from pathlib import Path
from typing import Optional

from ...logger import Logger
from ...storage import Storage
from .workdir import WorkDir
from .diskfree import get_free_space


class Datastore:
    def __init__(self, **params):
        if not params.get('path'):
            raise ValueError("No path parameter")
        
        self.config = params.get('config')
        self.path = str(Path(params['path']).resolve())
        self.logger = params.get('logger') or Logger()
        
        if not self.path:
            raise ValueError("No datastore path")
        
        # Datastore uses a 'deploy' subdirectory
        self.path = str(Path(self.path) / "deploy")
        
        # P2P network storage (lazy initialized)
        self._p2pnetstorage = None
        self._save_expiration = None
    
    def cleanUp(self) -> int:
        """Clean up expired files and directories, return remaining count"""
        if not Path(self.path).is_dir():
            return 0
        
        # Find storage directories for file parts
        storage_dirs = []
        
        # Private file parts
        private_pattern = str(Path(self.path) / "fileparts" / "private" / "*")
        storage_dirs.extend(glob.glob(private_pattern))
        
        # Shared file parts  
        shared_pattern = str(Path(self.path) / "fileparts" / "shared" / "*")
        storage_dirs.extend(glob.glob(shared_pattern))
        
        # Remove entire workdir
        workdir_path = Path(self.path) / "workdir"
        if workdir_path.exists():
            shutil.rmtree(str(workdir_path), ignore_errors=True)
        
        # Check if disk is full after workdir cleanup
        disk_is_full = self.diskIsFull()
        
        # Use one minute time frame for retention checking
        timeframe = time.time() - (time.time() % 60)
        remaining = 0
        
        for dir_path in storage_dirs:
            dir_path = Path(dir_path)
            
            if not dir_path.is_dir():
                # Remove non-directory files
                try:
                    dir_path.unlink()
                except:
                    pass
                continue
            
            # Extract timestamp from directory name
            try:
                timestamp = int(dir_path.name)
            except ValueError:
                continue
            
            # Remove if disk full or past retention time
            if disk_is_full or timeframe >= timestamp:
                try:
                    shutil.rmtree(str(dir_path), ignore_errors=True)
                except:
                    pass
            else:
                remaining += 1
        
        # Remove entire datastore path if no remaining file parts
        if remaining == 0:
            try:
                shutil.rmtree(self.path, ignore_errors=True)
            except:
                pass
        
        return remaining
    
    def createWorkDir(self, uuid: str) -> Optional['WorkDir']:
        """Create and return a work directory for the given UUID"""
        if not uuid:
            return None
        
        work_path = Path(self.path) / "workdir" / uuid
        
        try:
            work_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.logger.error(f"Failed to create work directory {work_path}: {e}")
            return None
        
        if not work_path.is_dir():
            return None
        
        return WorkDir(
            path=str(work_path),
            logger=self.logger
        )
    
    def diskIsFull(self) -> bool:
        """Check if disk space is below threshold (2GB)"""
        if not Path(self.path).is_dir():
            return False
        
        try:
            free_space = get_free_space(
                path=self.path,
                logger=self.logger
            )
        except Exception as e:
            self.logger.debug2(f"Error getting free space: {e}")
            free_space = None
        
        if free_space is None:
            self.logger.debug2('free_space is None!')
            free_space = 0
        
        self.logger.debug(f"Free space on {self.path}: {free_space}")
        
        # Return True if less than 2GB (2000MB) free
        return free_space < 2000
    
    def getP2PNet(self) -> Optional[dict]:
        """Get P2P network peer information from storage"""
        if not self._p2pnetstorage:
            if not self.config or not self.config.get('vardir'):
                return None
            
            try:
                self._p2pnetstorage = Storage(
                    logger=self.logger,
                    directory=self.config['vardir']
                )
            except Exception as e:
                self.logger.error(f"Failed to create P2P storage: {e}")
                return None
        
        if not self._p2pnetstorage:
            return None
        
        try:
            return self._p2pnetstorage.restore(name="p2pnet")
        except Exception as e:
            self.logger.error(f"Failed to restore P2P network data: {e}")
            return None
    
    def saveP2PNet(self, peers: dict):
        """Save P2P network peer information to storage"""
        if not self._p2pnetstorage or not peers:
            return
        
        # Don't save too often - use 60 second throttling
        current_time = time.time()
        if self._save_expiration and current_time <= self._save_expiration:
            return
        
        try:
            self._p2pnetstorage.save(name="p2pnet", data=peers)
            self._save_expiration = current_time + 60
        except Exception as e:
            self.logger.error(f"Failed to save P2P network data: {e}")