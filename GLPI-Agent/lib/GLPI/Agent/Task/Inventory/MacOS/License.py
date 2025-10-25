"""
GLPI Agent Task Inventory MacOS License Module

This module collects software license information on macOS systems.
Supports Adobe, Transmit, and VMware licenses.
"""

import os
import re
import glob
import subprocess
from typing import Dict, Any, Optional, List


class License:
    """MacOS License inventory module."""
    
    @staticmethod
    def category():
        """Return the category for this inventory module."""
        return "licenseinfo"
    
    def is_enabled(self, **params):
        """
        Check if this module can run on the current system.
        
        Returns:
            bool: Always True for macOS systems.
        """
        return True
    
    def do_inventory(self, **params):
        """
        Perform the license inventory and add results to inventory.
        
        Args:
            **params: Keyword arguments including:
                - inventory: The inventory object to add entries to
                - logger: Optional logger object for logging
                - scan_homedirs: Whether to scan user home directories
        """
        inventory = params.get('inventory')
        logger = params.get('logger')
        scan_homedirs = params.get('scan_homedirs', False)
        
        found = []
        
        # Adobe licenses
        file_adobe = '/Library/Application Support/Adobe/Adobe PCD/cache/cache.db'
        if os.path.isfile(file_adobe):
            # Try with sqlite3
            adobe_licenses = self._get_adobe_licenses(
                command=f'sqlite3 -separator " <> " "{file_adobe}" "SELECT * FROM domain_data"',
                logger=logger
            )
            found.extend(adobe_licenses)
            
            # If no licenses found, try without sqlite
            if len(adobe_licenses) == 0:
                adobe_licenses_alt = self._get_adobe_licenses_without_sqlite(
                    file_adobe, 
                    logger=logger
                )
                found.extend(adobe_licenses_alt)
        
        # Transmit licenses
        transmit_files = glob.glob('/System/Library/User Template/*.lproj/Library/Preferences/com.panic.Transmit.plist')
        
        if scan_homedirs:
            transmit_files.extend(glob.glob('/Users/*/Library/Preferences/com.panic.Transmit.plist'))
        else:
            if logger:
                logger.info(
                    "'scan-homedirs' configuration parameters disabled, "
                    "ignoring transmit installations in user directories"
                )
        
        for transmit_file in sorted(transmit_files):
            info = self._get_transmit_licenses(
                command=f"plutil -convert xml1 -o - '{transmit_file}'",
                logger=logger
            )
            if info:
                found.append(info)
                break  # One installation per machine
        
        # VMware licenses
        vmware_files = glob.glob('/Library/Application Support/VMware Fusion/license-*')
        for vmware_file in sorted(vmware_files):
            info_dict = {}
            
            lines = self._get_all_lines(file=vmware_file, logger=logger)
            if not lines:
                continue
            
            for line in lines:
                # Match lines like: LicenseType = "Site"
                match = re.match(r'^(\S+)\s+=\s+"(.*)"', line)
                if match:
                    info_dict[match.group(1)] = match.group(2)
            
            if not info_dict.get('Serial'):
                continue
            
            date = None
            last_modified = info_dict.get('LastModified', '')
            # Match format: 2021-05-15 @ 14:30
            match = re.match(r'^(2\d{3})-(\d{1,2})-(\d{1,2}) @ (\d{1,2}):(\d{1,2})', last_modified)
            if match:
                date = self._get_formatted_date(
                    int(match.group(1)),  # year
                    int(match.group(2)),  # month
                    int(match.group(3)),  # day
                    int(match.group(4)),  # hour
                    int(match.group(5)),  # minute
                    0  # second
                )
            
            found.append({
                'NAME': info_dict.get('ProductID'),
                'FULLNAME': f"{info_dict.get('ProductID')} ({info_dict.get('LicenseVersion')})",
                'KEY': info_dict.get('Serial'),
                'ACTIVATION_DATE': date
            })
        
        # Add all found licenses to inventory
        for license_info in found:
            inventory.add_entry(section='LICENSEINFOS', entry=license_info)
    
    def _get_adobe_licenses(self, **params):
        """
        Get Adobe licenses from sqlite database.
        
        Args:
            **params: Keyword arguments including:
                - command: sqlite3 command to execute
                - logger: Optional logger object
        
        Returns:
            list: List of license dictionaries
        """
        # This would need the actual Adobe license parsing logic
        # which depends on the getAdobeLicenses function from Tools::License
        # For now, return empty list as placeholder
        return []
    
    def _get_adobe_licenses_without_sqlite(self, file_path, **params):
        """
        Get Adobe licenses without using sqlite (fallback method).
        
        Args:
            file_path: Path to Adobe cache database
            **params: Keyword arguments including:
                - logger: Optional logger object
        
        Returns:
            list: List of license dictionaries
        """
        # This would need the actual Adobe license parsing logic
        # which depends on the getAdobeLicensesWithoutSqlite function
        # For now, return empty list as placeholder
        return []
    
    def _get_transmit_licenses(self, **params):
        """
        Get Transmit license information from plist file.
        
        Args:
            **params: Keyword arguments including:
                - command: plutil command to execute
                - logger: Optional logger object
        
        Returns:
            dict: License information dictionary, or None
        """
        lines = self._get_all_lines(**params)
        if not lines:
            return None
        
        val = {}
        in_key = None
        
        for line in lines:
            if in_key:
                # Look for <string> value
                match = re.search(r'<string>([\d\w\.-]+)</string>', line)
                if match:
                    val[in_key] = match.group(1)
                in_key = None
            elif '<key>SerialNumber2' in line:
                in_key = 'KEY'
            elif '<key>PreferencesVersion</key>' in line:
                in_key = 'VERSION'
        
        if not val.get('KEY'):
            return None
        
        return {
            'NAME': 'Transmit',
            'FULLNAME': "Panic's Transmit",
            'KEY': val['KEY']
        }
    
    def _get_formatted_date(self, year, month, day, hour, minute, second):
        """
        Format a date in the expected format.
        
        Args:
            year: Year
            month: Month (1-12)
            day: Day (1-31)
            hour: Hour (0-23)
            minute: Minute (0-59)
            second: Second (0-59)
        
        Returns:
            str: Formatted date string (e.g., "2021-05-15 14:30:00")
        """
        return f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"
    
    def _get_all_lines(self, **params):
        """
        Execute a command and return all output lines, or read from file.
        
        Args:
            **params: Keyword arguments including:
                - command: List or string command to execute
                - file: Optional file path to read from
                - logger: Optional logger object
        
        Returns:
            list: List of output lines
        """
        file_path = params.get('file')
        logger = params.get('logger')
        
        # If file is specified, read from it
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read().splitlines()
            except Exception as e:
                if logger:
                    logger.error(f"Error reading file {file_path}: {e}")
                return []
        
        command = params.get('command')
        if not command:
            return []
        
        # Ensure command is a list
        if isinstance(command, str):
            # Use shell=True for complex commands with pipes/redirects
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode != 0:
                    return []
                
                return result.stdout.splitlines()
            
            except subprocess.TimeoutExpired:
                if logger:
                    logger.error(f"Command timed out: {command}")
                return []
            except Exception as e:
                if logger:
                    logger.debug(f"Error executing command: {e}")
                return []
        
        # Command is already a list
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return []
            
            return result.stdout.splitlines()
        
        except subprocess.TimeoutExpired:
            if logger:
                logger.error(f"Command timed out: {' '.join(command)}")
            return []
        except FileNotFoundError:
            return []
        except Exception as e:
            if logger:
                logger.debug(f"Error executing command: {e}")
            return []

