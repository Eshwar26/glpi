#!/usr/bin/env python3
"""
Update Sysobject IDs - Python Implementation

Updates the sysobject.ids file from upstream sources and updates the changelog.
Converted from the original Perl implementation.
"""

import sys
import os
import hashlib
import subprocess
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    print("ERROR: requests module required", file=sys.stderr)
    print("Install it with: pip install requests", file=sys.stderr)
    sys.exit(1)

# Add lib and tools to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
sys.path.insert(0, str(Path(__file__).parent))

try:
    from Changelog import Changelog
except ImportError as e:
    print(f"ERROR: Failed to import required modules: {e}", file=sys.stderr)
    sys.exit(1)


SYSOBJECT_IDS_FILE = "share/sysobject.ids"
SYSOBJECT_IDS_URL = "https://raw.githubusercontent.com/glpi-project/sysobject.ids/master/sysobject.ids"


def get_file_sha1(file_path: str) -> Optional[str]:
    """
    Calculate SHA1 hash of file.
    
    Args:
        file_path: Path to file
    
    Returns:
        SHA1 hash as hex string
    """
    try:
        sha1 = hashlib.sha1()
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(65536)  # Read in 64KB chunks
                if not data:
                    break
                sha1.update(data)
        return sha1.hexdigest()
    except Exception as e:
        print(f"Warning: Failed to calculate hash for {file_path}: {e}", file=sys.stderr)
        return None


def get_git_last_commit_date(file_path: str) -> Optional[str]:
    """
    Get last commit date for a file using git.
    
    Args:
        file_path: Path to file
    
    Returns:
        Date string or None
    """
    try:
        cmd = ['git', 'log', '-n', '1', '--format=format:%aD', file_path]
        result = subprocess.run(
            cmd, 
            check=False, 
            capture_output=True, 
            text=True,
            env={**os.environ, 'LANG': 'C'}
        )
        
        if result.returncode == 0 and result.stdout:
            return result.stdout.strip()
    except Exception:
        pass
    
    return None


def touch_file_with_date(file_path: str, date: str) -> bool:
    """
    Update file modification time using touch command.
    
    Args:
        file_path: Path to file
        date: Date string
    
    Returns:
        True if successful
    """
    try:
        cmd = ['touch', '-d', date, file_path]
        result = subprocess.run(cmd, check=False, capture_output=True)
        return result.returncode == 0
    except Exception:
        # touch may not be available on Windows
        return False


def download_sysobject_ids(output_path: str) -> bool:
    """
    Download sysobject.ids file using mirror functionality.
    
    Args:
        output_path: Path to save file to
    
    Returns:
        True if downloaded (changed), False if not modified or error
    """
    try:
        # Use mirror functionality - only download if changed
        headers = {}
        if os.path.exists(output_path):
            # Get file modification time
            mtime = os.path.getmtime(output_path)
            from datetime import datetime
            dt = datetime.utcfromtimestamp(mtime)
            headers['If-Modified-Since'] = dt.strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        response = requests.get(SYSOBJECT_IDS_URL, headers=headers)
        
        if response.status_code == 304:
            # Not modified
            return False
        
        response.raise_for_status()
        
        # Save the file
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        return True
    
    except requests.RequestException as e:
        print(f"ERROR: Failed to download sysobject.ids: {e}", file=sys.stderr)
        return False


def main():
    """Main function."""
    # Touch sysobject.ids file with last commit date to make mirror API work
    if os.path.exists(SYSOBJECT_IDS_FILE):
        date = get_git_last_commit_date(SYSOBJECT_IDS_FILE)
        if date:
            touch_file_with_date(SYSOBJECT_IDS_FILE, date)
    
    # Calculate hash before download
    old_digest = None
    if os.path.exists(SYSOBJECT_IDS_FILE):
        old_digest = get_file_sha1(SYSOBJECT_IDS_FILE)
    
    # Download sysobject.ids
    downloaded = download_sysobject_ids(SYSOBJECT_IDS_FILE)
    
    if not downloaded:
        print("share/sysobject.ids is still up-to-date")
        return 0
    
    # Check if content actually changed
    new_digest = get_file_sha1(SYSOBJECT_IDS_FILE)
    
    if old_digest and new_digest and old_digest == new_digest:
        print("share/sysobject.ids is still up-to-date")
        return 0
    
    # Update changelog
    try:
        changelog = Changelog(file="Changes")
        changelog.add(**{"netdiscovery/netinventory": "Updated sysobject.ids"})
        changelog.write()
        print("Updated Changes file with sysobject.ids update")
    except Exception as e:
        print(f"Warning: Failed to update Changes file: {e}", file=sys.stderr)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

