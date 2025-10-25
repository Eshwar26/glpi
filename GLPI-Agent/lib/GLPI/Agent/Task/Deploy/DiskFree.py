import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from ....logger import Logger


def get_free_space(path: str, logger: Optional[Logger] = None) -> Optional[int]:
    """Get free space in MB for the given path"""
    if sys.platform.startswith('win'):
        return _get_free_space_windows(path, logger)
    elif sys.platform == 'sunos5':  # Solaris
        return _get_free_space_solaris(path, logger)
    else:
        return _get_free_space_unix(path, logger)


def remove_tree(folder: str) -> bool:
    """Remove directory tree, returns True if successful"""
    if not Path(folder).exists():
        return True
    
    try:
        shutil.rmtree(folder)
        return not Path(folder).exists()
    except Exception:
        # Fall back to manual removal
        try:
            folder_path = Path(folder)
            
            # Remove all files first
            for root, dirs, files in os.walk(folder, topdown=False):
                for file in files:
                    try:
                        Path(root) / file.unlink()
                    except:
                        pass
                
                # Remove directories
                for dir_name in dirs:
                    try:
                        (Path(root) / dir_name).rmdir()
                    except:
                        pass
            
            # Remove root directory
            try:
                folder_path.rmdir()
            except:
                pass
            
            return not folder_path.exists()
            
        except Exception:
            return False


def _get_free_space_windows(path: str, logger: Optional[Logger] = None) -> Optional[int]:
    """Get free space on Windows using WMI"""
    try:
        import wmi
        
        # Extract drive letter
        if not path or len(path) < 2 or path[1] != ':':
            if logger:
                logger.error(f"Path parse error: {path}")
            return None
        
        drive_letter = path[0] + ':'
        
        # Query WMI for disk info
        c = wmi.WMI()
        for disk in c.Win32_LogicalDisk():
            if disk.Caption and disk.Caption.lower() == drive_letter.lower():
                if disk.FreeSpace:
                    # Convert bytes to MB
                    free_space_mb = int(disk.FreeSpace) // (1024 * 1024)
                    return free_space_mb
        
        return None
        
    except ImportError:
        # Fall back to shutil.disk_usage if wmi not available
        try:
            usage = shutil.disk_usage(path)
            return usage.free // (1024 * 1024)  # Convert to MB
        except Exception as e:
            if logger:
                logger.error(f"Failed to get disk usage: {e}")
            return None
    
    except Exception as e:
        if logger:
            logger.error(f"Failed to get Windows free space: {e}")
        return None


def _get_free_space_solaris(path: str, logger: Optional[Logger] = None) -> Optional[int]:
    """Get free space on Solaris using df -b"""
    if not Path(path).is_dir():
        return None
    
    try:
        result = subprocess.run(
            ['df', '-b', path],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                # Look for pattern: device blocks used available ...
                parts = line.split()
                if len(parts) >= 4 and parts[3].isdigit():
                    # Available space in 512-byte blocks, convert to MB
                    available_blocks = int(parts[3])
                    available_mb = (available_blocks * 512) // (1024 * 1024)
                    return available_mb
        
        return None
        
    except Exception as e:
        if logger:
            logger.error(f"Failed to get Solaris free space: {e}")
        return None


def _get_free_space_unix(path: str, logger: Optional[Logger] = None) -> Optional[int]:
    """Get free space on Unix/Linux using df -Pk"""
    if not Path(path).is_dir():
        return None
    
    try:
        result = subprocess.run(
            ['df', '-Pk', path],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                # Parse the data line (skip header)
                data_line = lines[-1]  # Last line contains the data
                parts = data_line.split()
                
                if len(parts) >= 4 and parts[3].isdigit():
                    # Available space in KB, convert to MB
                    available_kb = int(parts[3])
                    available_mb = available_kb // 1024
                    return available_mb
        
        return None
        
    except Exception as e:
        if logger:
            logger.error(f"Failed to get Unix free space: {e}")
        return None