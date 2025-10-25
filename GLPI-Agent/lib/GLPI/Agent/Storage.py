#!/usr/bin/env python3
"""
GLPI Agent Storage - Python Implementation

This module handles persistent storage of data structures for the GLPI Agent.
Uses pickle for serialization (equivalent to Perl's Storable module).
"""

import os
import pickle
import shutil
import time
from pathlib import Path
from typing import Any, Dict, Optional

# Try different import paths for Logger
try:
    from .logger import Logger
except ImportError:
    try:
        from glpi_agent.logger import Logger
    except ImportError:
        # Fallback to basic logger
        class Logger:
            def error(self, msg): print(f"[ERROR] {msg}")
            def debug(self, msg): print(f"[DEBUG] {msg}")


class Storage:
    """
    Persistent storage manager for GLPI Agent.
    
    Handles saving and restoring data structures to disk,
    with support for migration from old storage locations.
    """
    
    def __init__(self, **params):
        """
        Initialize storage.
        
        Args:
            **params: Parameters including:
                - directory: Storage directory path (required)
                - logger: Logger instance (optional)
                - oldvardir: Old storage directory for migration (optional)
                - read_only: If True, skip write permission check (optional)
                
        Raises:
            ValueError: If directory parameter not provided
            RuntimeError: If directory cannot be created or is not writable
        """
        directory = params.get('directory')
        if not directory:
            raise ValueError("no directory parameter")
        
        self.directory: str = directory
        self.logger: Logger = params.get('logger') or Logger()
        self._mtime: Dict[str, float] = {}
        self._error: Optional[str] = None
        
        # Create directory if it doesn't exist
        if not Path(directory).is_dir():
            try:
                Path(directory).mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise RuntimeError(f"Can't create {directory}: {e}")
            
            # Migrate files from oldvardir if exists
            oldvardir = params.get('oldvardir')
            if oldvardir and Path(oldvardir).is_dir():
                self._migrateVarDir(oldvardir, directory)
        
        # Check write permissions (unless read-only mode)
        if not params.get('read_only', False) and not os.access(directory, os.W_OK):
            raise RuntimeError(f"Can't write in {directory}")
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"Storage(directory='{self.directory}')"
    
    def _migrateVarDir(self, from_dir: str, to_dir: str) -> None:
        """
        Migrate vardir content tree from old location to new.
        
        Args:
            from_dir: Source directory path
            to_dir: Destination directory path
        """
        if not (from_dir and Path(from_dir).is_dir() and 
                to_dir and Path(to_dir).is_dir()):
            return

        from_path = Path(from_dir)
        to_path = Path(to_dir)
        deletedirs = [from_path]

        self.logger.debug(f"Migrating storage from {from_dir} to {to_dir}")

        # Walk through source directory (bottom-up for proper deletion)
        for root, dirs, files in os.walk(from_dir, topdown=False):
            root_path = Path(root)

            # If the directory itself is a symlink, remove it and skip
            if root_path.is_symlink():
                try:
                    root_path.unlink()
                    self.logger.debug(f"Removed symlink directory: {root_path}")
                except Exception as e:
                    self.logger.error(f"Failed to remove symlink {root_path}: {e}")
                continue

            # Skip the root directory itself
            if root == from_dir:
                continue

            # Calculate relative path and destination
            rel_path = root_path.relative_to(from_path)
            dest_dir = to_path / rel_path

            # Create destination directory if needed
            if not dest_dir.exists():
                try:
                    dest_dir.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    self.logger.error(f"Failed to create directory {dest_dir}: {e}")
                    continue

            # Move files from source to destination
            for file in files:
                src_file = root_path / file
                dest_file = dest_dir / file
                
                if src_file.is_symlink():
                    # Remove symlinks rather than following them
                    try:
                        src_file.unlink()
                        self.logger.debug(f"Removed symlink file: {src_file}")
                    except Exception as e:
                        self.logger.error(f"Failed to remove symlink {src_file}: {e}")
                else:
                    # Move regular files
                    try:
                        shutil.move(str(src_file), str(dest_file))
                        self.logger.debug(f"Migrated: {src_file} -> {dest_file}")
                    except Exception as e:
                        self.logger.error(f"Failed to migrate {src_file}: {e}")

            # Track directories for deletion (in reverse order)
            deletedirs.insert(0, root_path)

        # Remove old directories (from deepest to shallowest)
        for dir_path in deletedirs:
            try:
                if dir_path.exists() and not any(dir_path.iterdir()):
                    dir_path.rmdir()
                    self.logger.debug(f"Removed old directory: {dir_path}")
            except Exception as e:
                self.logger.debug(f"Could not remove directory {dir_path}: {e}")

    def getDirectory(self) -> str:
        """
        Get the underlying directory for this storage.
        
        Returns:
            Storage directory path
        """
        return self.directory
    
    def _getFilePath(self, **params) -> str:
        """
        Get full file path for a given name.
        
        Args:
            **params: Parameters including:
                - name: File name (required)
                
        Returns:
            Full path to storage file
            
        Raises:
            ValueError: If name parameter not provided
        """
        name = params.get('name')
        if not name:
            raise ValueError("no name parameter given")
        
        return f"{self.directory}/{name}.dump"
    
    def has(self, **params) -> bool:
        """
        Check if a saved data structure exists.
        
        Args:
            **params: Parameters including:
                - name: File name to check
                
        Returns:
            True if file exists, False otherwise
        """
        file_path = self._getFilePath(**params)
        return Path(file_path).is_file()
    
    def _cache_mtime(self, file_path: str) -> None:
        """
        Cache file modification time.
        
        Args:
            file_path: Path to file
        """
        try:
            stat = Path(file_path).stat()
            self._mtime[file_path] = stat.st_mtime
        except Exception:
            pass
    
    def modified(self, **params) -> bool:
        """
        Check if file was modified since last access.
        
        Args:
            **params: Parameters including:
                - name: File name to check
                
        Returns:
            True if file was modified since last cached mtime
        """
        file_path = self._getFilePath(**params)
        
        if file_path not in self._mtime:
            return False
        
        try:
            stat = Path(file_path).stat()
            return stat.st_mtime > self._mtime[file_path]
        except Exception:
            return False
    
    def error(self, error: Optional[str] = None) -> Optional[str]:
        """
        Set or get last error.
        
        Args:
            error: Error message to set (if provided)
            
        Returns:
            Last error message (and clears it)
        """
        if error is not None:
            self._error = error
            return error
        
        # Return and clear last error
        last_error = self._error
        self._error = None
        return last_error
    
    def save(self, **params) -> None:
        """
        Save given data structure to disk.
        
        Args:
            **params: Parameters including:
                - name: File name for storage
                - data: Data structure to save
        """
        file_path = self._getFilePath(**params)
        data = params.get('data')
        
        try:
            # Use pickle protocol 4 for compatibility and performance
            with open(file_path, 'wb') as f:
                pickle.dump(data, f, protocol=4)
            self._cache_mtime(file_path)
            self.logger.debug(f"Saved data to {file_path}")
        except Exception as e:
            error_msg = f"Can't save {file_path}: {e}"
            self.error(error_msg)
            self.logger.error(error_msg)
            # Cache current time to prevent repeated save attempts
            self._mtime[file_path] = time.time()
    
    def restore(self, **params) -> Any:
        """
        Restore a saved data structure from disk.
        
        Args:
            **params: Parameters including:
                - name: File name to restore
                
        Returns:
            Restored data structure, or None if not found or corrupted
        """
        file_path = self._getFilePath(**params)
        
        if not Path(file_path).is_file():
            return None
        
        result = None
        try:
            with open(file_path, 'rb') as f:
                result = pickle.load(f)
            self.logger.debug(f"Restored data from {file_path}")
        except Exception as e:
            self.logger.error(
                f"Can't read corrupted {file_path}, removing it ({e})"
            )
            try:
                Path(file_path).unlink()
            except Exception as unlink_error:
                self.logger.error(
                    f"Failed to remove corrupted file: {unlink_error}"
                )
        
        self._cache_mtime(file_path)
        return result
    
    def remove(self, **params) -> None:
        """
        Delete the file containing a serialized data structure.
        
        Args:
            **params: Parameters including:
                - name: File name to remove
        """
        file_path = self._getFilePath(**params)
        
        try:
            Path(file_path).unlink()
            self.logger.debug(f"Removed {file_path}")
        except FileNotFoundError:
            # File already doesn't exist, that's fine
            pass
        except Exception as e:
            self.logger.error(f"Can't unlink {file_path}: {e}")
        
        # Remove from mtime cache
        self._mtime.pop(file_path, None)


if __name__ == "__main__":
    # Basic test
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(directory=tmpdir)
        print(f"Created storage: {storage}")
        
        # Test save/restore
        test_data = {'key': 'value', 'list': [1, 2, 3]}
        storage.save(name='test', data=test_data)
        
        restored = storage.restore(name='test')
        print(f"Saved and restored: {restored}")
        
        # Test has
        print(f"Has 'test': {storage.has(name='test')}")
        print(f"Has 'nonexistent': {storage.has(name='nonexistent')}")
        
        # Test remove
        storage.remove(name='test')
        print(f"After removal, has 'test': {storage.has(name='test')}")