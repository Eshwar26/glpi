#!/usr/bin/env python3
"""
VirusTotal Report Analysis - Python Implementation

Checks VirusTotal reports for given files or SHA256 hashes.
Converted from the original Perl implementation.
"""

import sys
import os
import json
import time
import hashlib
import argparse
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

try:
    import requests
except ImportError:
    print("ERROR: requests module required", file=sys.stderr)
    print("Install it with: pip install requests", file=sys.stderr)
    sys.exit(1)


VIRUSTOTAL_BASE_URL = "https://www.virustotal.com/api/v3/files"


def calculate_sha256(file_path: str) -> Optional[str]:
    """
    Calculate SHA256 hash of a file.
    
    Args:
        file_path: Path to file
    
    Returns:
        SHA256 hash as hex string or None on error
    """
    try:
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(65536)  # Read in 64KB chunks
                if not data:
                    break
                sha256.update(data)
        return sha256.hexdigest()
    except Exception as e:
        print(f"shasum: {file_path}: {e}", file=sys.stderr)
        return None


def get_virustotal_report(sha256: str, api_key: str, debug: bool = False) -> Optional[Dict]:
    """
    Get VirusTotal report for a SHA256 hash.
    
    Args:
        sha256: SHA256 hash
        api_key: VirusTotal API key
        debug: Enable debug output
    
    Returns:
        Report data or None
    """
    url = f"{VIRUSTOTAL_BASE_URL}/{sha256}"
    
    if debug:
        print(f"{datetime.now()}: debug: requesting {url}...")
    
    try:
        headers = {'x-apikey': api_key}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        return response.json()
    
    except requests.RequestException as e:
        print(f"{datetime.now()}: {url} error: {e}", file=sys.stderr)
        return None


def check_report(sha256: str, label: str, api_key: str, debug: bool = False,
                path: Optional[str] = None) -> Optional[bool]:
    """
    Check a VirusTotal report for malicious results.
    
    Args:
        sha256: SHA256 hash
        label: Label for the file (for logging)
        api_key: VirusTotal API key
        debug: Enable debug output
        path: Optional path to save report JSON
    
    Returns:
        True if safe, False if malicious, None if report not ready
    """
    report = get_virustotal_report(sha256, api_key, debug)
    
    if not report:
        return None
    
    # Check if report has expected structure
    try:
        data = report.get('data', {})
        attributes = data.get('attributes', {})
        last_analysis_results = attributes.get('last_analysis_results', {})
        
        # Check if VBA32 is in results (as mentioned in original script)
        if 'VBA32' not in last_analysis_results:
            # Analysis may still be running
            if 'error' in report:
                error_code = report['error'].get('code', 'unknown')
                print(f"{datetime.now()}: Report error code{label}: {error_code}")
            else:
                print(f"{datetime.now()}: Analysis is running{label}")
            return None
        
        # Get stats
        last_analysis_stats = attributes.get('last_analysis_stats', {})
        suspicious = last_analysis_stats.get('suspicious', 0)
        malicious = last_analysis_stats.get('malicious', 0)
        
        # Save report if path provided
        if path:
            report_file = os.path.join(path, f"{sha256}.json")
            try:
                with open(report_file, 'w', encoding='utf-8') as f:
                    json.dump(report, f, indent=2)
            except Exception as e:
                print(f"{datetime.now()}: Can't write {report_file}: {e}", file=sys.stderr)
        
        # Check for malicious results
        if suspicious or malicious:
            print(f"{datetime.now()}: Got malicious analysis reporting{label}")
            vt_url = f"https://www.virustotal.com/gui/file/{sha256}"
            print(f"::warning title=Malicious analysis reporting{label}::See {vt_url}")
            return False
        else:
            print(f"{datetime.now()}: No malicious analysis reporting{label}")
            return True
    
    except Exception as e:
        print(f"{datetime.now()}: Error parsing report{label}: {e}", file=sys.stderr)
        return None


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Check VirusTotal reports for files or SHA256 hashes'
    )
    parser.add_argument(
        '--sha256',
        action='append',
        dest='sha256_list',
        help='SHA256 hash to check'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug output'
    )
    parser.add_argument(
        '--path',
        help='Change to this directory and save reports there'
    )
    parser.add_argument(
        'files',
        nargs='*',
        help='Files to calculate SHA256 and check'
    )
    
    args = parser.parse_args()
    
    # Check for API key
    api_key = os.environ.get('VT_API_KEY')
    if not api_key:
        print("Set VT_API_KEY environment variable to your VirusTotal API Key "
              "if you want to check VirusTotal reports.", file=sys.stderr)
        return 0
    
    # Change to path if specified
    if args.path:
        try:
            os.chdir(args.path)
        except Exception as e:
            print(f"ERROR: Can't change directory to {args.path}: {e}", file=sys.stderr)
            return 1
    
    # Collect SHA256 hashes
    sha256_dict: Dict[str, str] = {}  # sha256 -> label
    
    # Add from --sha256 arguments
    if args.sha256_list:
        for sha256 in args.sha256_list:
            sha256_dict[sha256] = ""
    
    # Add from files
    for file_path in args.files:
        if os.path.exists(file_path):
            sha256 = calculate_sha256(file_path)
            if sha256:
                if args.debug:
                    print(f"debug: {file_path} sha256: {sha256}")
                sha256_dict[sha256] = f" for {file_path}"
        else:
            print(f"No such '{file_path}' file", file=sys.stderr)
    
    # Check if we have anything to verify
    if not sha256_dict:
        print("No VirusTotal report to verify", file=sys.stderr)
        return 2
    
    # Check reports with retry logic
    sha256_list = list(sha256_dict.keys())
    failed: List[str] = []
    
    first = len(sha256_list)
    max_tries = 20 * first
    tries = max_tries
    timeout = time.time() + 600  # 10 minutes
    wait_time = 15  # seconds
    next_try_time = 0
    
    while time.time() < timeout and sha256_list and tries > 0:
        if time.time() >= next_try_time and sha256_list:
            sha256 = sha256_list.pop(0)
            label = sha256_dict[sha256]
            
            result = check_report(
                sha256, label, api_key, args.debug,
                args.path or os.getcwd()
            )
            
            if result is None:
                # Report not ready, try again later
                sha256_list.append(sha256)
            elif result is False:
                # Malicious
                failed.append(sha256)
            # else: result is True, safe - nothing to do
            
            # Set next try time
            first -= 1
            next_try_time = time.time() + (0 if first > 0 else wait_time)
            tries -= 1
        else:
            time.sleep(1)
    
    # Print summary
    if failed:
        count = len(failed)
        plural = "s" if count > 1 else ""
        print(f"{datetime.now()}: Got malicious VirusTotal analysis reporting for "
              f"{count} file{plural}.")
    else:
        print(f"{datetime.now()}: VirusTotal analysis reporting seems good.")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

