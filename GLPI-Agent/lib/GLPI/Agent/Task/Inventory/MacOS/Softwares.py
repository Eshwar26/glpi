"""
GLPI Agent Task Inventory MacOS Softwares Module

This module collects installed software information on macOS systems.
"""

import re
import time
import subprocess
from typing import Dict, Any, Optional, List, Tuple


class Softwares:
    """MacOS Softwares inventory module."""
    
    @staticmethod
    def category():
        """Return the category for this inventory module."""
        return "software"
    
    def is_enabled(self, **params):
        """
        Check if this module can run on the current system.
        
        Returns:
            bool: True if /usr/sbin/system_profiler command is available.
        """
        return self._can_run('/usr/sbin/system_profiler')
    
    def do_inventory(self, **params):
        """
        Perform the software inventory and add results to inventory.
        
        Args:
            **params: Keyword arguments including:
                - inventory: The inventory object to add entries to
                - logger: Optional logger object for logging
        """
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        softwares = self._get_softwares_list(logger=logger)
        
        if not softwares:
            return
        
        for software in softwares:
            inventory.add_entry(
                section='SOFTWARES',
                entry=software
            )
    
    def _get_softwares_list(self, **params):
        """
        Get list of installed software.
        
        Args:
            **params: Keyword arguments including:
                - logger: Optional logger object
        
        Returns:
            list: List of software dictionaries
        """
        logger = params.get('logger')
        
        # Note: In the Perl version, this uses XML format with getSystemProfilerInfos
        # For simplicity, we'll use the text format here
        # A full implementation would parse XML format for more accurate data
        
        local_time_offset = self._detect_local_time_offset()
        
        lines = self._get_all_lines(
            command='/usr/sbin/system_profiler SPApplicationsDataType',
            logger=logger
        )
        
        if not lines:
            return []
        
        softwares = []
        current_app = None
        app_name = None
        
        for line in lines:
            # Application name (indented once)
            if line.startswith('    ') and not line.startswith('      ') and line.strip().endswith(':'):
                if current_app and app_name:
                    software = self._process_application(app_name, current_app)
                    if software:
                        softwares.append(software)
                
                app_name = line.strip().rstrip(':')
                current_app = {}
                continue
            
            if current_app is not None and line.startswith('      '):
                # Property line (indented twice)
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    if value:
                        current_app[key] = value
        
        # Process last application
        if current_app and app_name:
            software = self._process_application(app_name, current_app)
            if software:
                softwares.append(software)
        
        return softwares
    
    def _process_application(self, name, app):
        """
        Process an application and extract software information.
        
        Args:
            name: Application name
            app: Application properties dictionary
        
        Returns:
            dict: Software information dictionary, or None if should be skipped
        """
        # Skip Windows applications found by Parallels (issue #716)
        get_info_string = app.get('Get Info String', '')
        if get_info_string and re.match(r'^\S+, [A-Z]:\\', get_info_string):
            return None
        
        version = app.get('Version', '')
        # Cleanup dotted version from spaces (e.g., "1 . 0" -> "1.0")
        if version:
            version = re.sub(r' \. ', '.', version)
        
        soft = {
            'NAME': name,
            'VERSION': version,
        }
        
        # Determine publisher
        publisher = self._determine_publisher(name, app)
        if publisher:
            soft['PUBLISHER'] = publisher
        
        # Add install date if available
        if app.get('Last Modified'):
            soft['INSTALLDATE'] = app['Last Modified']
        
        # Add architecture if available
        if app.get('Kind'):
            soft['ARCH'] = app['Kind']
        
        # Extract system category and username from location
        location = app.get('Location', '')
        category, username = self._extract_software_system_category_and_user_name(location)
        if category:
            soft['SYSTEM_CATEGORY'] = category
        if username:
            soft['USERNAME'] = username
        
        return soft
    
    def _determine_publisher(self, name, app):
        """
        Determine the software publisher from various sources.
        
        Args:
            name: Application name
            app: Application properties dictionary
        
        Returns:
            str: Publisher name, or None
        """
        source = app.get('Obtained from', '')
        location = app.get('Location', '')
        
        # Check if from Apple
        if source == 'Apple' or (location and re.search(r'/System/Library/(CoreServices|Frameworks)/', location)):
            return 'Apple'
        
        # Check if from Identified Developer
        if source == 'Identified Developer' and app.get('Signed by'):
            signed_by = app['Signed by']
            match = re.match(r'^Developer ID Application: ([^,]*),?', signed_by)
            if match:
                developer = match.group(1)
                
                # Remove parenthetical content
                sub_match = re.match(r'^(.*)\s+\(.*\)$', developer)
                if sub_match:
                    developer = sub_match.group(1)
                
                # Clean up common suffixes
                developer = re.sub(r'\s*Incorporated.*', ' Inc.', developer, flags=re.IGNORECASE)
                developer = re.sub(r'\s*Corporation.*', '', developer, flags=re.IGNORECASE)
                
                if developer.strip():
                    return developer.strip()
        
        # Try to guess publisher from copyright in Get Info String
        get_info_string = app.get('Get Info String', '')
        if get_info_string:
            publisher = self._extract_publisher_from_info_string(get_info_string)
            if publisher:
                return publisher
        
        # Try canonical manufacturer from Get Info String
        if get_info_string:
            editor = self._get_canonical_manufacturer(get_info_string)
            if editor and editor != get_info_string:
                return editor
        
        # Finally, try canonical manufacturer from name
        editor = self._get_canonical_manufacturer(name)
        if editor and editor != name:
            return editor
        
        return None
    
    def _extract_publisher_from_info_string(self, info_string):
        """
        Extract publisher from Get Info String copyright information.
        
        Args:
            info_string: Get Info String value
        
        Returns:
            str: Publisher name, or None
        """
        # Split by comma
        parts = [p.strip() for p in info_string.split(',')]
        
        # Check if Apple is mentioned
        if any(re.search(r'\bApple\b', p, re.IGNORECASE) for p in parts):
            return 'Apple'
        
        # Look for copyright information
        copyright_parts = [p for p in parts if re.search(r'(\(C\)|\u00a9|Copyright|\ufeff)', p, re.IGNORECASE)]
        
        if copyright_parts:
            publisher = copyright_parts[0]
            
            # Extract "by XXX" if present
            match = re.search(r'\sby\s(.*)', publisher, re.IGNORECASE)
            if match:
                publisher = match.group(1)
            
            # Remove copyright symbols and text
            publisher = re.sub(r'.*(\(C\)|\u00a9|Copyright|\ufeff)\s*', '', publisher, flags=re.IGNORECASE)
            publisher = re.sub(r'\s*All rights reserved\.?\s*', '', publisher, flags=re.IGNORECASE)
            publisher = re.sub(r'\s*Incorporated.*', ' Inc.', publisher, flags=re.IGNORECASE)
            publisher = re.sub(r'\s*Corporation.*', '', publisher, flags=re.IGNORECASE)
            # Remove years
            publisher = re.sub(r'\s*\d+(\s*-\s*\d+)?\s*', '', publisher)
            
            publisher = publisher.strip()
            if publisher:
                return publisher
        
        return None
    
    def _extract_software_system_category_and_user_name(self, location):
        """
        Extract system category and username from application location path.
        
        Args:
            location: Application location path
        
        Returns:
            tuple: (category, username) both can be None
        """
        if not location:
            return (None, None)
        
        category = None
        username = None
        
        # Match /Users/username/category1/category2/...
        match = re.match(r'^/Users/([^/]+)/([^/]+/[^/]+)/', location)
        if not match:
            match = re.match(r'^/Users/([^/]+)/([^/]+)/', location)
        
        if match:
            username = match.group(1)
            category = match.group(2) if len(match.groups()) >= 2 else None
            # Skip Downloads and Desktop
            if category and re.match(r'^(Downloads|Desktop)', category):
                category = None
        else:
            # Match /Volumes/... or /category/...
            match = re.match(r'^/Volumes/[^/]+/([^/]+/[^/]+)/', location)
            if not match:
                match = re.match(r'^/Volumes/[^/]+/([^/]+)/', location)
            if not match:
                match = re.match(r'^/([^/]+/[^/]+)/', location)
            if not match:
                match = re.match(r'^/([^/]+)/', location)
            
            if match:
                category = match.group(1)
        
        return (category, username)
    
    def _get_canonical_manufacturer(self, text):
        """
        Get canonical manufacturer name from text.
        
        This is a simplified version. The full implementation would use
        a manufacturer database.
        
        Args:
            text: Text to extract manufacturer from
        
        Returns:
            str: Canonical manufacturer name
        """
        if not text:
            return text
        
        # Simple manufacturer detection
        known_manufacturers = {
            'apple': 'Apple',
            'microsoft': 'Microsoft',
            'google': 'Google',
            'adobe': 'Adobe',
            'mozilla': 'Mozilla',
        }
        
        text_lower = text.lower()
        for key, value in known_manufacturers.items():
            if key in text_lower:
                return value
        
        return text
    
    def _detect_local_time_offset(self):
        """
        Detect local time offset from GMT.
        
        Returns:
            int: Time offset in seconds
        """
        import time
        if time.localtime().tm_isdst:
            return time.altzone
        else:
            return time.timezone
    
    def _get_all_lines(self, **params):
        """
        Execute a command and return all output lines.
        
        Args:
            **params: Keyword arguments including:
                - command: List or string command to execute
                - logger: Optional logger object
        
        Returns:
            list: List of output lines from the command
        """
        command = params.get('command')
        logger = params.get('logger')
        
        if not command:
            return []
        
        # Ensure command is a list
        if isinstance(command, str):
            command = command.split()
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=120  # Software inventory can take longer
            )
            
            if result.returncode != 0:
                if logger:
                    logger.warning(
                        f"Command failed with return code {result.returncode}: {' '.join(command)}"
                    )
                return []
            
            return result.stdout.splitlines()
        
        except subprocess.TimeoutExpired:
            if logger:
                logger.error(f"Command timed out: {' '.join(command)}")
            return []
        except FileNotFoundError:
            if logger:
                logger.error(f"Command not found: {command[0]}")
            return []
        except Exception as e:
            if logger:
                logger.error(f"Error executing command: {e}")
            return []
    
    def _can_run(self, command):
        """
        Check if a command can be run (exists and is executable).
        
        Args:
            command: Path to command to check
        
        Returns:
            bool: True if command exists and is executable
        """
        import os
        return os.path.isfile(command) and os.access(command, os.X_OK)

