import hashlib
import os
import shutil
import time
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

from ....logger import Logger

if TYPE_CHECKING:
    from .datastore import Datastore
    from ....http.fusion_client import FusionClient


class File:
    def __init__(self, **params):
        if not params.get('datastore'):
            raise ValueError("No datastore parameter")
        if not params.get('sha512'):
            raise ValueError("No sha512 parameter")
        
        data = params.get('data', {})
        
        self.p2p = data.get('p2p', False)
        self.retention_duration = data.get('p2p-retention-duration', 0)
        self.prolog_delay = params.get('prolog', 3600)
        self.uncompress = data.get('uncompress', False)
        self.mirrors = data.get('mirrors', [])
        self.multiparts = data.get('multiparts', [])
        self.name = data.get('name', '')
        self.sha512 = params['sha512']
        self.datastore = params['datastore']
        self.client = params.get('client')
        self.logger = params.get('logger') or Logger()
        
        # Set default retention duration based on p2p setting
        if not self.retention_duration:
            if self.p2p:
                # For p2p files, keep downloaded parts 3 days by default
                self.retention_duration = 60 * 24 * 3
            else:
                # For non-p2p files, keep as long as needed:
                # 3 times the PROLOG delay to support download restart
                self.retention_duration = 0
        
        # Will be set during prepare phase
        self.name_local = None
        
        # P2P network instance (lazy loaded)
        self.p2pnet = None
    
    def normalizedPartFilePath(self, sha512: str) -> Optional[str]:
        """Get normalized file path for a part based on SHA512"""
        if len(sha512) < 9 or not sha512[:9].replace('0123456789abcdef', ''):
            return None
        
        # Create subdirectory structure from SHA512: a/b/cdefgh/
        sub_file_path = Path(sha512[0]) / sha512[1] / sha512[2:8]
        
        # Determine storage location based on p2p setting
        file_path = Path(self.datastore.path) / 'fileparts'
        
        if self.p2p:
            file_path = file_path / 'shared'
            retention_duration = self.retention_duration * 60
        else:
            file_path = file_path / 'private'
            retention_duration = (self.retention_duration * 60 
                                if self.retention_duration 
                                else self.prolog_delay * 3)
        
        # Compute expiration time with one-minute time frame
        expiration = time.time() + retention_duration + 60
        retention_time = int(expiration - (expiration % 60))
        
        file_path = file_path / str(retention_time) / sub_file_path
        
        return str(file_path)
    
    def _cleanPath(self, path: str, max_levels: int = 5):
        """Clean up empty parent directories"""
        path_obj = Path(path)
        parent = path_obj.parent
        
        levels = 0
        while levels < max_levels and parent != parent.parent:
            try:
                parent.rmdir()  # Only removes if empty
                parent = parent.parent
                levels += 1
            except OSError:
                break  # Directory not empty or other error
    
    def cleanup_private(self):
        """Clean up private file parts if no retention duration set"""
        # Don't cleanup for p2p shared parts
        if self.p2p:
            return
        
        # Only cleanup if no retention duration has been set
        if self.retention_duration:
            return
        
        # Clean up all parts
        for sha512 in self.multiparts:
            path = self.getPartFilePath(sha512)
            path_obj = Path(path)
            
            if path_obj.is_file():
                try:
                    path_obj.unlink()
                    self._cleanPath(path)
                except:
                    pass
    
    def resetPartFilePaths(self):
        """Move all part files to respect retention duration from now"""
        updates = {}
        
        for sha512 in self.multiparts:
            current_path = self.getPartFilePath(sha512)
            if Path(current_path).is_file():
                new_path = self.normalizedPartFilePath(sha512)
                if new_path and current_path != new_path:
                    updates[current_path] = new_path
        
        # Perform the moves
        for old_path, new_path in updates.items():
            try:
                # Create parent directories
                Path(new_path).parent.mkdir(parents=True, exist_ok=True)
                
                # Move file
                shutil.move(old_path, new_path)
                
                # Clean up old path
                self._cleanPath(old_path)
            except Exception as e:
                self.logger.error(f"Failed to move {old_path} to {new_path}: {e}")
    
    def getPartFilePath(self, sha512: str) -> str:
        """Get current file path for a part, checking existing storage locations"""
        if len(sha512) < 9:
            return self.normalizedPartFilePath(sha512) or ""
        
        # Create subdirectory path from SHA512
        sub_file_path = Path(sha512[0]) / sha512[1] / sha512[2:8]
        
        # Check all possible storage directories
        base_path = Path(self.datastore.path) / 'fileparts'
        
        # Search in shared directories
        shared_pattern = str(base_path / 'shared' / '*')
        for storage_dir in Path(base_path / 'shared').glob('*'):
            if storage_dir.is_dir():
                file_path = storage_dir / sub_file_path
                if file_path.is_file():
                    return str(file_path)
        
        # Search in private directories
        for storage_dir in Path(base_path / 'private').glob('*'):
            if storage_dir.is_dir():
                file_path = storage_dir / sub_file_path
                if file_path.is_file():
                    return str(file_path)
        
        # Return normalized path if not found
        return self.normalizedPartFilePath(sha512) or ""
    
    def download(self):
        """Download all file parts from mirrors and P2P peers"""
        if not self.mirrors:
            self.logger.error("No mirror set on deploy job")
            raise RuntimeError("No mirrors configured")
        
        # Get configuration from datastore
        config = getattr(self.datastore, 'config', {})
        port = config.get('httpd-port', 62354)
        workers = max(config.get('remote-workers', 10), 10)
        
        # Try to set up P2P if enabled
        peers = []
        if self.p2p:
            try:
                # This would require implementing the P2P module
                # For now, we'll skip P2P functionality
                self.logger.debug("P2P functionality not implemented in Python version")
            except Exception as e:
                self.logger.debug(f"Failed to enable P2P: {e}")
        
        last_peer = None
        next_path_update = self._getNextPathUpdateTime()
        
        # Download each part
        for sha512 in self.multiparts:
            path = self.getPartFilePath(sha512)
            
            # Skip if file exists and validates
            if Path(path).is_file() and self._getSha512ByFile(path) == sha512:
                continue
            
            # Create parent directory
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            
            # Try last successful peer first
            if last_peer:
                if self._downloadPeer(last_peer, sha512, path, port):
                    continue
            
            # Try all peers
            success = False
            for peer in peers:
                if self._downloadPeer(peer, sha512, path, port):
                    last_peer = peer
                    success = True
                    break
                
                # Update file path periodically during long searches
                if time.time() > next_path_update:
                    new_path = self.normalizedPartFilePath(sha512)
                    if new_path:
                        path = new_path
                    next_path_update = self._getNextPathUpdateTime()
            
            if success:
                continue
            
            # Try mirrors
            for mirror in self.mirrors:
                if self._download(mirror, sha512, path):
                    success = True
                    break
                
                # Update file path periodically
                if time.time() > next_path_update:
                    new_path = self.normalizedPartFilePath(sha512)
                    if new_path:
                        path = new_path
                    next_path_update = self._getNextPathUpdateTime()
            
            # Check if we failed to download
            if not success:
                if not last_peer and not peers and not self.mirrors:
                    self.logger.debug("Can't download part as no mirror is defined")
                    self.logger.debug("You probably missed to enable the GLPI option to use GLPI server as a mirror")
                    self.logger.error("Aborting download: no mirror")
                    break
    
    def _getNextPathUpdateTime(self) -> float:
        """Get next path update time (aligned to minute boundary)"""
        current_time = time.time()
        return current_time + 60 - (current_time % 60)
    
    def _downloadPeer(self, peer: str, sha512: str, path: str, port: int) -> bool:
        """Download from a P2P peer"""
        source = f"http://{peer}:{port}/deploy/getFile/"
        return self._download(source, sha512, path, peer)
    
    def _download(self, source: str, sha512: str, path: str, peer: Optional[str] = None) -> bool:
        """Download a file part from a source URL"""
        if not source.startswith(('http://', 'https://')):
            self.logger.error(f"Source or mirror is not a valid URL: {source}")
            return False
        
        if len(sha512) < 2:
            return False
        
        # Create SHA512 directory structure
        sha512_dir = f"{sha512[0]}/{sha512[0]}{sha512[1]}/"
        
        # Ensure source URL ends with slash
        if not source.endswith('/'):
            source += '/'
        
        url = f"{source}{sha512_dir}{sha512}"
        self.logger.debug(f"File part URL: {url}")
        
        # Set timeout based on whether this is a peer or mirror
        timeout = 1 if peer else 180
        
        try:
            # Make HTTP request
            if self.client:
                # Use the existing HTTP client
                response = self.client.request('GET', url, timeout=timeout)
                
                if response.status_code != 200:
                    if peer and (response.status_code != 404 or 'Nothing found' in response.text):
                        self.logger.debug2(f"Remote peer {peer} is useless, we should forget it for a while")
                        if self.p2pnet:
                            self.p2pnet.forgetPeer(peer)
                    return False
                
                # Write response content to file
                with open(path, 'wb') as f:
                    f.write(response.content)
            else:
                # Fall back to basic HTTP request
                import requests
                response = requests.get(url, timeout=timeout)
                
                if response.status_code != 200:
                    return False
                
                with open(path, 'wb') as f:
                    f.write(response.content)
        
        except Exception as e:
            self.logger.debug(f"Download failed for {url}: {e}")
            return False
        
        # Verify file exists
        if not Path(path).is_file():
            return False
        
        # Validate SHA512
        if self._getSha512ByFile(path) != sha512:
            self.logger.debug(f"SHA512 failure: {sha512}")
            try:
                Path(path).unlink()
            except:
                pass
            return False
        
        return True
    
    def filePartsExists(self) -> bool:
        """Check if all file parts exist"""
        for sha512 in self.multiparts:
            file_path = self.getPartFilePath(sha512)
            if not Path(file_path).is_file():
                return False
        return True
    
    def _getSha512ByFile(self, file_path: str) -> Optional[str]:
        """Calculate SHA512 hash of a file"""
        try:
            sha512_hash = hashlib.sha512()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha512_hash.update(chunk)
            return sha512_hash.hexdigest()
        except Exception as e:
            self.logger.debug(f"SHA512 failure: {e}")
            return None
    
    def validateFileByPath(self, file_path: str) -> bool:
        """Validate a file against its expected SHA512"""
        if Path(file_path).is_file():
            return self._getSha512ByFile(file_path) == self.sha512
        return False