#!/usr/bin/env python3
"""
Changelog - Python Implementation

This module provides changelog management functionality for the GLPI Agent.
Converted from the original Perl implementation.
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Optional

# Add lib to path if running from tools directory
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))

try:
    from GLPI.Agent.Tools import get_all_lines, get_first_match
except ImportError:
    # Fallback for standalone usage
    def get_all_lines(file: str = None, **kwargs) -> List[str]:
        """Fallback implementation for get_all_lines."""
        if file and os.path.exists(file):
            with open(file, 'r', encoding='utf-8') as f:
                return f.read().splitlines()
        return []
    
    def get_first_match(pattern: str, file: str = None, **kwargs) -> Optional[str]:
        """Fallback implementation for get_first_match."""
        import re
        if file and os.path.exists(file):
            lines = get_all_lines(file=file)
            compiled_pattern = re.compile(pattern)
            for line in lines:
                match = compiled_pattern.search(line)
                if match:
                    groups = match.groups()
                    return groups[0] if groups else match.group(0)
        return None


class Changelog:
    """Changelog file manager."""
    
    def __init__(self, file: str):
        """
        Initialize Changelog with file path.
        
        Args:
            file: Path to the changelog file
        """
        if not file or not os.path.exists(file):
            raise ValueError(f"No valid file parameter: {file}")
        
        self._file = file
        self._first_lines: List[str] = []
        self._last_lines: List[str] = []
        self._sections: List[str] = []
        self._section_content: Dict[str, List[str]] = {}
        
        # Parse the changelog file
        self._parse_file()
    
    def _parse_file(self):
        """Parse the changelog file."""
        lines = get_all_lines(file=self._file)
        if not lines:
            return
        
        section = None
        in_release_section = False
        
        for line in lines:
            if self._last_lines:
                # Already in last_lines section, add everything
                self._last_lines.append(line)
            elif section is None and not in_release_section:
                # Check if this is the start of "not yet released" section
                if 'not yet released' in line.lower() or 'not release yet' in line.lower():
                    in_release_section = True
                self._first_lines.append(line)
            elif not line.strip():
                # Empty line, reset section
                section = ""
            elif line and not line[0].isspace() and line.endswith(':'):
                # New section header (e.g., "inventory:", "core:")
                section = line.rstrip(':')
                if section not in self._sections:
                    self._sections.append(section)
                if section not in self._section_content:
                    self._section_content[section] = []
            elif section is not None and section != "":
                # Content line in a section
                if section not in self._section_content:
                    self._section_content[section] = []
                self._section_content[section].append(line)
            elif section == "":
                # Content after empty line but before new section = end of changes
                self._last_lines.append(line)
    
    def add(self, **params):
        """
        Add entries to changelog sections.
        
        Args:
            **params: Section name -> entry text mapping
        """
        for section, entry in params.items():
            # Add section if it doesn't exist
            if section not in self._sections:
                self._sections.append(section)
            
            # Initialize section content if needed
            if section not in self._section_content:
                self._section_content[section] = []
            
            # Add the entry with bullet point
            self._section_content[section].append(f"* {entry}")
    
    def write(self, file: Optional[str] = None):
        """
        Write changelog to file.
        
        Args:
            file: Optional output file path (defaults to original file)
        """
        output_file = file or self._file
        
        with open(output_file, 'w', encoding='utf-8', newline='\n') as f:
            # Write first lines (header)
            for line in self._first_lines:
                f.write(f"{line}\n")
            
            # Write sections with content
            for section in self._sections:
                if section in self._section_content and self._section_content[section]:
                    f.write(f"\n{section}:\n")
                    for line in self._section_content[section]:
                        f.write(f"{line}\n")
            
            # Write separator and last lines
            f.write("\n")
            for line in self._last_lines:
                f.write(f"{line}\n")
    
    def task_version_update(self, task: str) -> bool:
        """
        Update task version in changelog.
        
        Args:
            task: Task name (e.g., 'Inventory', 'NetDiscovery')
        
        Returns:
            True if version was bumped, False otherwise
        """
        # Determine section name
        if task in ['NetDiscovery', 'NetInventory']:
            section = 'netdiscovery/netinventory'
        else:
            section = task.lower()
        
        # Check if version was already bumped manually
        if section in self._section_content:
            for line in self._section_content[section]:
                if f"Bump {task} task version to" in line:
                    return False
        
        # Check for previous version bumps in last_lines
        previous = None
        for line in self._last_lines:
            if f"Bump {task} task version to" in line:
                import re
                match = re.search(f"Bump {task} task version to (.*)$", line)
                if match:
                    previous = match.group(1)
                    break
        
        # Try to get latest version from task module
        try:
            module_name = f"GLPI.Agent.Task.{task}.Version"
            module = __import__(module_name, fromlist=['VERSION'])
            latest = getattr(module, 'VERSION', None)
            if callable(latest):
                latest = latest()
        except (ImportError, AttributeError):
            return False
        
        if not latest:
            return False
        
        if previous and latest == previous:
            return False
        
        # Add version bump entry
        self.add(**{section: f"Bump {task} task version to {latest}"})
        return True
    
    def httpd_plugin_version_update(self, plugin: str) -> bool:
        """
        Update HTTPD plugin version in changelog.
        
        Args:
            plugin: Plugin name (e.g., 'BasicAuthentication', 'Inventory')
        
        Returns:
            True if version was bumped, False otherwise
        """
        # Section mapping
        httpd_plugin_section_mapping = {
            'BasicAuthentication': 'basic-authentication-server-plugin',
            'Inventory': 'inventory-server-plugin',
            'Proxy': 'proxy-server-plugin',
            'SSL': 'ssl-server-plugin',
            'Test': 'test-server-plugin',
        }
        
        section = httpd_plugin_section_mapping.get(plugin, plugin.lower())
        
        # Check if version was already bumped manually
        if section in self._section_content:
            for line in self._section_content[section]:
                if f"Bump {plugin} plugin version to" in line:
                    return False
        
        # Check for previous version bumps in last_lines
        previous = None
        for line in self._last_lines:
            if f"Bump {plugin} plugin version to" in line:
                import re
                match = re.search(f"Bump {plugin} plugin version to (.*)$", line)
                if match:
                    previous = match.group(1)
                    break
        
        # Try to get latest version from plugin module
        try:
            module_name = f"GLPI.Agent.HTTP.Server.{plugin}"
            module = __import__(module_name, fromlist=['VERSION'])
            latest = getattr(module, 'VERSION', None)
        except (ImportError, AttributeError):
            return False
        
        if not latest:
            return False
        
        if previous and latest == previous:
            return False
        
        # Add version bump entry
        self.add(**{section: f"Bump {plugin} plugin version to {latest}"})
        return True


if __name__ == '__main__':
    # Simple test
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        changelog = Changelog(sys.argv[1])
        print(f"Loaded changelog from {sys.argv[1]}")
        print(f"Sections: {', '.join(changelog._sections)}")
    else:
        print("Usage: Changelog.py <changelog_file>")
