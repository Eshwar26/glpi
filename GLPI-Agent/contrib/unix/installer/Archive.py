#!/usr/bin/env python3
"""Archive - Embedded archive handling for installer"""

import os
import sys
from typing import List, Dict, Optional, BinaryIO


class Archive:
    """Archive class for handling embedded files in installer"""
    
    def __init__(self, data_handle=None):
        """
        Initialize archive from DATA section or file handle.
        
        Args:
            data_handle: Optional file handle to read embedded data from
        """
        self._files: List[str] = []
        self._len: Dict[str, int] = {}
        self._datas: Dict[str, bytes] = {}
        
        # If data handle is provided, read from it
        if data_handle and hasattr(data_handle, 'read'):
            # Read files list from DATA section
            # Format: filename:length pairs
            files_spec = []
            for line in data_handle:
                line = line.strip()
                if line and not line.startswith('#'):
                    if ':' in line:
                        name, length = line.split(':', 1)
                        files_spec.append((name.strip(), int(length.strip())))
            
            # Read actual file data
            for name, length in files_spec:
                buffer = data_handle.read(length)
                if len(buffer) != length:
                    raise IOError(f"Failed to read archive: expected {length} bytes, got {len(buffer)}")
                
                self._files.append(name)
                self._len[name] = length
                self._datas[name] = buffer
    
    def files(self) -> List[str]:
        """
        Get list of file names in archive.
        
        Returns:
            List of file names
        """
        return self._files.copy()
    
    def list(self):
        """List all files in archive with their sizes and exit"""
        for name in self._files:
            length = self._len.get(name, 0)
            print(f"{name:<60}    {length:>8} bytes")
        sys.exit(0)
    
    def content(self, filename: str) -> Optional[bytes]:
        """
        Get content of a file from archive.
        
        Args:
            filename: Name of file to get content for
            
        Returns:
            File content as bytes, or None if not found
        """
        return self._datas.get(filename)
    
    def extract(self, filename: str, dest: Optional[str] = None) -> bool:
        """
        Extract a file from archive.
        
        Args:
            filename: Name of file to extract
            dest: Optional destination path (default: extract filename from path)
            
        Returns:
            True if extraction successful, False otherwise
        """
        if not self._datas:
            raise ValueError("No embedded archive")
        
        if filename not in self._datas:
            raise ValueError(f"No such {filename} file in archive")
        
        # Determine destination filename
        if dest:
            name = dest
        else:
            # Extract filename from path
            if '/' in filename:
                name = filename.split('/')[-1]
            elif '\\' in filename:
                name = filename.split('\\')[-1]
            else:
                name = filename
            
            if not name:
                raise ValueError(f"Can't extract name from {filename}")
        
        # Remove existing file if present
        if os.path.exists(name):
            os.unlink(name)
        
        # Write file
        try:
            with open(name, 'wb') as out:
                out.write(self._datas[filename])
            
            # Verify size
            file_size = os.path.getsize(name)
            expected_size = self._len.get(filename, 0)
            return file_size == expected_size
        except IOError as e:
            raise IOError(f"Can't write {name}: {e}")

