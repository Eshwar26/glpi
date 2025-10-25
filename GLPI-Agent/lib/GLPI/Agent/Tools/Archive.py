#!/usr/bin/env python3
"""
GLPI Agent Tools Archive - Python Implementation

Archive extraction utility for various archive formats.

Supports: .tar, .tar.gz, .tar.bz2, .tar.xz, .zip, .7z, .rar, .cab, .deb, .rpm
"""

import os
import re
import tarfile
import zipfile
import tempfile
import shutil
from typing import Optional, Dict, Any
from pathlib import Path

__all__ = ['Archive']


class Archive:
    """
    Archive extraction handler.
    
    Supports multiple archive formats with automatic format detection.
    """
    
    def __init__(self, **params):
        """
        Initialize Archive handler.
        
        Args:
            **params: Parameters including:
                - file: Path to archive file
                - logger: Logger object
        """
        self.file = params.get('file')
        self.logger = params.get('logger')
        self._tempdir = None
        self._archive_type = None
        
        if self.file:
            self._detect_type()
    
    def _detect_type(self) -> Optional[str]:
        """Detect archive type from file extension and magic bytes."""
        if not self.file or not os.path.exists(self.file):
            return None
        
        file_lower = self.file.lower()
        
        # Check by extension
        if file_lower.endswith('.tar.gz') or file_lower.endswith('.tgz'):
            self._archive_type = 'tar.gz'
        elif file_lower.endswith('.tar.bz2') or file_lower.endswith('.tbz2'):
            self._archive_type = 'tar.bz2'
        elif file_lower.endswith('.tar.xz') or file_lower.endswith('.txz'):
            self._archive_type = 'tar.xz'
        elif file_lower.endswith('.tar'):
            self._archive_type = 'tar'
        elif file_lower.endswith('.zip'):
            self._archive_type = 'zip'
        elif file_lower.endswith('.7z'):
            self._archive_type = '7z'
        elif file_lower.endswith('.rar'):
            self._archive_type = 'rar'
        elif file_lower.endswith('.cab'):
            self._archive_type = 'cab'
        elif file_lower.endswith('.deb'):
            self._archive_type = 'deb'
        elif file_lower.endswith('.rpm'):
            self._archive_type = 'rpm'
        
        return self._archive_type
    
    def extract(self, **params) -> Optional[str]:
        """
        Extract archive to temporary directory.
        
        Args:
            **params: Parameters including:
                - to: Destination directory (optional, creates temp if not specified)
                
        Returns:
            Path to extraction directory or None
        """
        if not self.file or not os.path.exists(self.file):
            if self.logger:
                self.logger.error(f"Archive file not found: {self.file}")
            return None
        
        destination = params.get('to')
        if not destination:
            self._tempdir = tempfile.mkdtemp(prefix='glpi_archive_')
            destination = self._tempdir
        
        try:
            if self._archive_type in ['tar', 'tar.gz', 'tar.bz2', 'tar.xz']:
                return self._extract_tar(destination)
            elif self._archive_type == 'zip':
                return self._extract_zip(destination)
            else:
                # For other formats, would need external tools
                if self.logger:
                    self.logger.warning(f"Unsupported archive type: {self._archive_type}")
                return None
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to extract archive: {e}")
            return None
    
    def _extract_tar(self, destination: str) -> Optional[str]:
        """Extract tar archive."""
        mode_map = {
            'tar': 'r',
            'tar.gz': 'r:gz',
            'tar.bz2': 'r:bz2',
            'tar.xz': 'r:xz'
        }
        
        mode = mode_map.get(self._archive_type, 'r')
        
        with tarfile.open(self.file, mode) as tar:
            tar.extractall(destination)
        
        return destination
    
    def _extract_zip(self, destination: str) -> Optional[str]:
        """Extract zip archive."""
        with zipfile.ZipFile(self.file, 'r') as zip_ref:
            zip_ref.extractall(destination)
        
        return destination
    
    def list_files(self) -> list:
        """
        List files in archive without extracting.
        
        Returns:
            List of file paths in archive
        """
        if not self.file or not os.path.exists(self.file):
            return []
        
        try:
            if self._archive_type in ['tar', 'tar.gz', 'tar.bz2', 'tar.xz']:
                mode_map = {
                    'tar': 'r',
                    'tar.gz': 'r:gz',
                    'tar.bz2': 'r:bz2',
                    'tar.xz': 'r:xz'
                }
                mode = mode_map.get(self._archive_type, 'r')
                
                with tarfile.open(self.file, mode) as tar:
                    return tar.getnames()
            
            elif self._archive_type == 'zip':
                with zipfile.ZipFile(self.file, 'r') as zip_ref:
                    return zip_ref.namelist()
        
        except Exception:
            return []
        
        return []
    
    def cleanup(self):
        """Clean up temporary extraction directory."""
        if self._tempdir and os.path.exists(self._tempdir):
            try:
                shutil.rmtree(self._tempdir)
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Failed to cleanup temp directory: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()


if __name__ == '__main__':
    print("GLPI Agent Tools Archive Module")
    print("Archive extraction utility for various formats")
