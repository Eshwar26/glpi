#!/usr/bin/env python3
"""
MSI Signing - Python Implementation

Signs Windows MSI installers using CodeSignTool from SSL.com.
Converted from the original Perl implementation.
"""

import sys
import os
import argparse
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    print("ERROR: requests module required", file=sys.stderr)
    print("Install it with: pip install requests", file=sys.stderr)
    sys.exit(1)


CODESIGNTOOL_VERSION = "CodeSignTool-v1.2.0-windows"
CODESIGNTOOL_URL = "https://www.ssl.com/download/29773/"


def download_file(url: str, output_path: str) -> bool:
    """
    Download file from URL using mirror functionality.
    
    Args:
        url: URL to download from
        output_path: Path to save file to
    
    Returns:
        True if successful
    """
    print(f"Downloading file '{url}'...")
    
    try:
        # Check if file exists and get headers
        head_response = requests.head(url, allow_redirects=True)
        
        if os.path.exists(output_path):
            # Check if local file is up to date
            local_size = os.path.getsize(output_path)
            remote_size = int(head_response.headers.get('content-length', 0))
            
            if local_size == remote_size:
                print("Already up to date")
                return True
        
        # Download the file
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return True
    
    except requests.RequestException as e:
        print(f"ERROR: Error getting {url}: {e}", file=sys.stderr)
        return False


def extract_zip(zip_path: str, extract_to: str, strip_prefix: str = None) -> bool:
    """
    Extract ZIP archive.
    
    Args:
        zip_path: Path to ZIP file
        extract_to: Directory to extract to
        strip_prefix: Optional prefix to strip from paths
    
    Returns:
        True if successful
    """
    print(f"Extracting {zip_path} archive...")
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_file:
            if strip_prefix:
                # Extract with stripping prefix
                for member in zip_file.namelist():
                    if member.startswith(strip_prefix):
                        # Remove prefix from member name
                        target_path = member[len(strip_prefix):].lstrip('/')
                        if target_path:
                            target_full_path = os.path.join(extract_to, target_path)
                            
                            # Create directories
                            os.makedirs(os.path.dirname(target_full_path), exist_ok=True)
                            
                            # Extract file
                            if not member.endswith('/'):
                                with zip_file.open(member) as source:
                                    with open(target_full_path, 'wb') as target:
                                        shutil.copyfileobj(source, target)
            else:
                zip_file.extractall(extract_to)
        
        return True
    
    except Exception as e:
        print(f"ERROR: Failed to extract {zip_path}: {e}", file=sys.stderr)
        return False


def sign_msi(folder: str, msi_filename: str) -> int:
    """
    Sign MSI file using CodeSignTool.
    
    Args:
        folder: Base folder path
        msi_filename: MSI filename
    
    Returns:
        0 on success, 1 on error
    """
    output_file = os.path.join(folder, 'output', msi_filename)
    
    if not os.path.exists(output_file):
        print(f"ERROR: No such '{output_file}' MSI file", file=sys.stderr)
        return 1
    
    # Check for required environment variables
    cst_credential_id = os.environ.get('CST_CREDENTIALID')
    cst_username = os.environ.get('CST_USERNAME')
    cst_password = os.environ.get('CST_PASSWORD')
    cst_secret = os.environ.get('CST_SECRET')
    
    if not all([cst_credential_id, cst_username, cst_password, cst_secret]):
        print(f"No authority setup to sign '{output_file}', skipping")
        return 0
    
    # Setup directories
    signed_folder = os.path.join(folder, 'download')
    signed_file = os.path.join(signed_folder, msi_filename)
    tools_folder = os.path.join(folder, 'tools')
    codesigntool_folder = os.path.join(tools_folder, 'CodeSignTool')
    
    os.makedirs(signed_folder, exist_ok=True)
    os.makedirs(tools_folder, exist_ok=True)
    
    # Download and extract CodeSignTool if needed
    if not os.path.isdir(codesigntool_folder):
        zipfile_path = os.path.join(signed_folder, f"{CODESIGNTOOL_VERSION}.zip")
        
        if not os.path.exists(zipfile_path):
            if not download_file(CODESIGNTOOL_URL, zipfile_path):
                return 1
        
        if not extract_zip(zipfile_path, codesigntool_folder, CODESIGNTOOL_VERSION):
            return 1
        
        if not os.path.isdir(codesigntool_folder):
            print(f"ERROR: Nothing extracted from {zipfile_path}", file=sys.stderr)
            return 1
    
    # Change to CodeSignTool directory
    original_dir = os.getcwd()
    try:
        os.chdir(codesigntool_folder)
        
        print("Running CodeSignTool.bat sign ...")
        
        # Build command
        cmd = [
            'CodeSignTool.bat', 'sign',
            f'-username={cst_username}',
            f'-password={cst_password}',
            f'-credential_id={cst_credential_id}',
            f'-totp_secret={cst_secret}',
            f'-input_file_path={output_file}',
            f'-output_dir_path={signed_folder}'
        ]
        
        # Run CodeSignTool
        result = subprocess.run(cmd, check=False)
        
        if result.returncode != 0:
            print(f"\nERROR: CodeSignTool failure", file=sys.stderr)
            return 1
        
        if not os.path.exists(signed_file):
            print(f"\nERROR: CodeSignTool failed to sign", file=sys.stderr)
            return 1
        
        # Move signed file back to output
        print(f"Updating {msi_filename} with signed version")
        shutil.move(signed_file, output_file)
        
    finally:
        os.chdir(original_dir)
    
    return 0


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Sign Windows MSI installer using CodeSignTool'
    )
    parser.add_argument(
        'folder',
        help='Base folder containing output directory'
    )
    parser.add_argument(
        'msi_file',
        help='MSI filename to sign'
    )
    
    args = parser.parse_args()
    
    if not args.folder:
        print("ERROR: No base folder given", file=sys.stderr)
        return 1
    
    if not args.msi_file:
        print("ERROR: No MSI filename given", file=sys.stderr)
        return 1
    
    if not os.path.isdir(args.folder):
        print(f"ERROR: No such '{args.folder}' base folder", file=sys.stderr)
        return 1
    
    return sign_msi(args.folder, args.msi_file)


if __name__ == '__main__':
    sys.exit(main())

