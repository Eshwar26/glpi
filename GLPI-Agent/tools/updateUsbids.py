#!/usr/bin/env python3
"""
Update USB IDs - Python Implementation

Updates the usb.ids file from upstream sources and updates the changelog.
Converted from the original Perl implementation.
"""

import sys
import os
import re
import subprocess
from pathlib import Path
from typing import Optional, Tuple

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


USB_IDS_FILE = "share/usb.ids"
USB_IDS_URL = "http://www.linux-usb.org/usb.ids"


def get_file_date_version(file_path: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extract date and version from usb.ids file.
    
    Args:
        file_path: Path to usb.ids file
    
    Returns:
        Tuple of (date, time, version)
    """
    date = None
    time = None
    version = None
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                if line.startswith('#'):
                    # Look for date line: #   Date:   YYYY-MM-DD HH:MM:SS
                    date_match = re.match(r'^#\s+Date:\s+([0-9-]+)\s+([0-9:]+)', line)
                    if date_match:
                        date = date_match.group(1)
                        time = date_match.group(2)
                    
                    # Look for version line: #   Version: X.Y.Z
                    version_match = re.match(r'^#\s+Version:\s+([0-9.]+)', line)
                    if version_match:
                        version = version_match.group(1)
                
                # Only check header lines
                if not line.startswith('#'):
                    break
    except Exception as e:
        print(f"Warning: Failed to read {file_path}: {e}", file=sys.stderr)
    
    return date, time, version


def touch_file_with_date(file_path: str, date: str, time: str) -> bool:
    """
    Update file modification time using touch command.
    
    Args:
        file_path: Path to file
        date: Date string (YYYY-MM-DD)
        time: Time string (HH:MM:SS)
    
    Returns:
        True if successful
    """
    try:
        # Use touch command with -d option (Linux/Unix)
        cmd = ['touch', '-d', f'{date} {time}', file_path]
        result = subprocess.run(cmd, check=False, capture_output=True)
        return result.returncode == 0
    except Exception:
        # touch may not be available on Windows
        return False


def download_usb_ids(output_path: str) -> bool:
    """
    Download usb.ids file using mirror functionality.
    
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
        
        response = requests.get(USB_IDS_URL, headers=headers)
        
        if response.status_code == 304:
            # Not modified
            return False
        
        response.raise_for_status()
        
        # Save the file
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        return True
    
    except requests.RequestException as e:
        print(f"ERROR: Failed to download usb.ids: {e}", file=sys.stderr)
        return False


def main():
    """Main function."""
    # Touch usb.ids file with stored date to make mirror API work as expected
    if os.path.exists(USB_IDS_FILE):
        date, time, _ = get_file_date_version(USB_IDS_FILE)
        if date and time:
            touch_file_with_date(USB_IDS_FILE, date, time)
    
    # Download usb.ids
    downloaded = download_usb_ids(USB_IDS_FILE)
    
    if not downloaded:
        print("share/usb.ids is still up-to-date")
        return 0
    
    # Get version from downloaded file
    _, _, version = get_file_date_version(USB_IDS_FILE)
    
    if not version:
        print("Warning: Could not extract version from usb.ids", file=sys.stderr)
        return 0
    
    # Check if already updated in Changes file
    previous_version = None
    if os.path.exists("Changes"):
        try:
            with open("Changes", 'r', encoding='utf-8') as f:
                for line in f:
                    match = re.search(r'Updated usb\.ids to ([0-9.]+) version', line)
                    if match:
                        previous_version = match.group(1)
                        break
        except Exception:
            pass
    
    if version == previous_version:
        print("share/usb.ids was still up-to-date")
        return 0
    
    # Update changelog
    try:
        changelog = Changelog(file="Changes")
        changelog.add(inventory=f"Updated usb.ids to {version} version")
        changelog.write()
        print(f"Updated Changes file with usb.ids version {version}")
    except Exception as e:
        print(f"Warning: Failed to update Changes file: {e}", file=sys.stderr)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

