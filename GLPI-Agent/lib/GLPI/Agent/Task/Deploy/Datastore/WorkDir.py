import gzip
import os
import shutil
import subprocess
from pathlib import Path
from typing import List, TYPE_CHECKING

from ....logger import Logger
from ....tools.archive import Archive

if TYPE_CHECKING:
    from .file import File


class WorkDir:
    def __init__(self, **params):
        self.path = params.get('path')
        self.logger = params.get('logger') or Logger()
        self.files = []
        
        if not self.path:
            raise ValueError("No path parameter provided")
        
        path_obj = Path(self.path)
        if not path_obj.is_dir():
            raise ValueError(f"Path '{self.path}' doesn't exist")
    
    def path(self) -> str:
        """Get the work directory path"""
        return self.path
    
    def addFile(self, file: 'File'):
        """Add a file to be processed in this work directory"""
        self.files.append(file)
    
    def prepare(self) -> bool:
        """Prepare work directory by assembling and extracting files"""
        logger = self.logger
        
        # Rebuild complete files from file parts
        for file in self.files:
            file.name_local = file.name
            
            # Handle Windows codepage conversion
            if os.name == 'nt':
                try:
                    # For Windows, we might need codepage conversion
                    # This is a simplified version - full implementation would
                    # require proper Windows codepage handling
                    file.name_local = file.name
                except:
                    file.name_local = file.name
            
            # Simplify filename for extraction
            if file.uncompress:
                short_sha512 = file.sha512[:6]
                
                # Replace with short SHA for tar.gz files
                if '.tar.gz' in file.name_local.lower():
                    file.name_local = f"{short_sha512}.tar.gz"
                else:
                    # Handle other archive extensions
                    for ext in ['.tar', '.gz', '.7z', '.bz2']:
                        if file.name_local.lower().endswith(ext):
                            file.name_local = f"{short_sha512}{ext}"
                            break
            
            final_file_path = Path(self.path) / file.name_local
            
            # Open final file for writing
            try:
                with open(final_file_path, 'wb') as fh:
                    for sha512 in file.multiparts:
                        part_file_path = file.getPartFilePath(sha512)
                        
                        if not Path(part_file_path).is_file():
                            logger.debug(f"Missing multipart element '{part_file_path}'")
                            continue
                        
                        try:
                            # Read gzipped part file
                            with gzip.open(part_file_path, 'rb') as part:
                                logger.debug(f"reading {sha512}")
                                while True:
                                    buf = part.read(1024)
                                    if not buf:
                                        break
                                    fh.write(buf)
                        except Exception as e:
                            logger.info(f"Failed to open '{part_file_path}': {e}")
                            return False
            
            except Exception as e:
                logger.debug(f"Failed to open '{final_file_path}': {e}")
                return False
            
            # Validate assembled file
            if not file.validateFileByPath(str(final_file_path)):
                logger.info(f"Failed to construct the final file: {final_file_path}")
                return False
        
        # Extract compressed files
        for file in self.files:
            final_file_path = Path(self.path) / file.name_local
            
            if file.uncompress:
                success = False
                
                # Try 7z first if available
                if self._can_run('7z'):
                    success = self._extract_with_7z(str(final_file_path))
                
                # Fall back to Python archive extraction
                if not success:
                    try:
                        archive = Archive(archive=str(final_file_path))
                        if archive:
                            success = archive.extract(to=self.path)
                        else:
                            logger.info("Failed to create Archive object")
                    except Exception as e:
                        logger.debug(f"Failed to extract '{final_file_path}': {e}")
                
                # Remove original compressed file after extraction
                try:
                    final_file_path.unlink()
                except:
                    pass
        
        return True
    
    def _can_run(self, command: str) -> bool:
        """Check if a command is available in PATH"""
        try:
            subprocess.run([command], capture_output=True, timeout=1)
            return True
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return False
    
    def _extract_with_7z(self, file_path: str) -> bool:
        """Extract file using 7z command"""
        try:
            # Extract with 7z
            result = subprocess.run([
                '7z', 'x', f'-o{self.path}', file_path
            ], capture_output=True, text=True, timeout=300)
            
            tarball = None
            for line in result.stdout.split('\n'):
                line = line.strip()
                self.logger.debug2(f"7z: {line}")
                if line.startswith('Extracting') and line.endswith('.tar'):
                    tarball = line.split()[-1]
            
            # If we extracted a tarball, extract that too
            if tarball and any(file_path.lower().endswith(ext) for ext in ['.tgz', '.tar.gz', '.tar.xz', '.tar.bz2']):
                tarball_path = Path(self.path) / tarball
                if tarball_path.exists():
                    result2 = subprocess.run([
                        '7z', 'x', f'-o{self.path}', str(tarball_path)
                    ], capture_output=True, text=True, timeout=300)
                    
                    for line in result2.stdout.split('\n'):
                        line = line.strip()
                        self.logger.debug2(f"7z: {line}")
                    
                    # Remove the intermediate tarball
                    try:
                        tarball_path.unlink()
                    except:
                        pass
            
            return result.returncode == 0
            
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError) as e:
            self.logger.debug(f"7z extraction failed: {e}")
            return False