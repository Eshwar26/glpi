"""
GLPI Agent Task Inventory MacOS Videos Module

This module collects video/graphics card information on macOS systems.
"""

import re
import subprocess
from typing import Dict, Any, Optional, List


class Videos:
    """MacOS Videos inventory module."""
    
    @staticmethod
    def category():
        """Return the category for this inventory module."""
        return "video"
    
    def is_enabled(self, **params):
        """
        Check if this module can run on the current system.
        
        Returns:
            bool: True if /usr/sbin/system_profiler command is available.
        """
        return self._can_run('/usr/sbin/system_profiler')
    
    def do_inventory(self, **params):
        """
        Perform the video card inventory and add results to inventory.
        
        Args:
            **params: Keyword arguments including:
                - inventory: The inventory object to add entries to
                - logger: Optional logger object for logging
        """
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        video_cards = self._get_video_cards(logger=logger)
        
        for video in video_cards:
            inventory.add_entry(
                section='VIDEOS',
                entry=video
            )
    
    def _get_video_cards(self, **params):
        """
        Get video card information.
        
        Args:
            **params: Keyword arguments including:
                - logger: Optional logger object
                - file: Optional file to read from
        
        Returns:
            list: List of video card dictionaries
        """
        logger = params.get('logger')
        
        infos = self._get_system_profiler_infos(
            type='SPDisplaysDataType',
            logger=logger,
            file=params.get('file')
        )
        
        graphics_displays = infos.get('Graphics/Displays', {})
        
        videos = []
        for video_name in sorted(graphics_displays.keys()):
            video_card_info = graphics_displays[video_name]
            
            # Get VRAM memory
            vram_str = (video_card_info.get('VRAM (Total)') or
                       video_card_info.get('VRAM (Dynamic, Max)'))
            memory = self._get_canonical_size(vram_str, 1024)
            
            # Remove any non-numeric suffix if present
            if memory:
                memory = re.sub(r'\s.*', '', str(memory))
            
            video = {
                'CHIPSET': video_card_info.get('Chipset Model'),
                'MEMORY': memory,
                'NAME': video_name
            }
            
            # Get resolution from displays
            displays = video_card_info.get('Displays', {})
            for display_name, display_info in displays.items():
                # Skip certain display types
                if display_name in ('Display Connector', 'Display'):
                    continue
                
                resolution = display_info.get('Resolution')
                if resolution:
                    # Parse resolution like "1920 x 1080" or "1920x1080"
                    match = re.match(r'(\d+)\s*x\s*(\d+)', resolution)
                    if match:
                        x, y = match.groups()
                        resolution = f"{x}x{y}"
                        
                        # Set first found resolution on associated video card
                        if not video.get('RESOLUTION'):
                            video['RESOLUTION'] = resolution
            
            # Set PCI slot info
            if video_card_info.get('Bus') is not None:
                video['PCISLOT'] = video_card_info['Bus']
            if video_card_info.get('Slot') is not None:
                video['PCISLOT'] = video_card_info['Slot']
            
            # Filter out None values
            video = {k: v for k, v in video.items() if v is not None}
            
            videos.append(video)
        
        return videos
    
    def _get_canonical_size(self, size_str, base=1024):
        """
        Convert size string to MB.
        
        Args:
            size_str: Size string like "2 GB" or "512 MB"
            base: Base for conversion (1024 or 1000)
        
        Returns:
            int: Size in MB, or None
        """
        if not size_str:
            return None
        
        # Match number and unit
        match = re.match(r'([\d.]+)\s*([KMGTP]?B?)', str(size_str), re.IGNORECASE)
        if not match:
            return None
        
        value = float(match.group(1))
        unit = match.group(2).upper()
        
        # Convert to MB
        if unit in ('B', 'BYTES'):
            value = value / (base * base)
        elif unit in ('K', 'KB', 'KIB'):
            value = value / base
        elif unit in ('M', 'MB', 'MIB'):
            pass  # Already in MB
        elif unit in ('G', 'GB', 'GIB'):
            value = value * base
        elif unit in ('T', 'TB', 'TIB'):
            value = value * base * base
        elif unit in ('P', 'PB', 'PIB'):
            value = value * base * base * base
        
        return int(value)
    
    def _get_system_profiler_infos(self, **params):
        """
        Get structured information from system_profiler command.
        
        Args:
            **params: Keyword arguments including:
                - type: The data type to query
                - logger: Optional logger object
                - file: Optional file to read from
        
        Returns:
            dict: Parsed system profiler information as nested dictionary
        """
        profiler_type = params.get('type', '')
        logger = params.get('logger')
        file_path = params.get('file')
        
        # Build command
        command = ['/usr/sbin/system_profiler']
        if profiler_type:
            command.append(profiler_type)
        
        # Get command output
        lines = self._get_all_lines(command=command, logger=logger, file=file_path)
        if not lines:
            return {}
        
        # Parse the output into a nested dictionary
        info = {}
        parents = [(info, -1, None)]
        
        for line in lines:
            # Match lines in format: "    Key: Value" or "    Key:"
            if ':' not in line:
                continue
            
            # Calculate indentation level
            stripped = line.lstrip()
            level = len(line) - len(stripped)
            
            # Split into key and value
            parts = line.split(':', 1)
            key = parts[0].strip()
            value = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
            
            # Get current parent
            parent_node, parent_level, _ = parents[-1]
            
            if value:
                # Check indentation level against parent node
                if level <= parent_level:
                    # Check if parent node is empty and needs cleanup
                    if len(parent_node) == 0 and len(parents) > 1:
                        parent_key = parents[-1][2]
                        if parent_key:
                            parents[-2][0][parent_key] = None
                    
                    # Unstack nodes until suitable parent is found
                    while len(parents) > 1 and level <= parents[-1][1]:
                        parents.pop()
                    parent_node = parents[-1][0]
                
                # Add the value to current node
                parent_node[key] = value
            else:
                # No value means this is a new section
                # Compare level with parent
                if level < parent_level:
                    # Up the tree: unstack until suitable parent found
                    while len(parents) > 1 and level <= parents[-1][1]:
                        parents.pop()
                elif level == parent_level:
                    # Same level: unstack last node
                    if len(parents) > 1:
                        parents.pop()
                # else: level > parent_level, down the tree, no change
                
                # Create new node and push to stack
                parent_node = parents[-1][0]
                
                # Handle duplicate keys
                original_key = key
                counter = 1
                while key in parent_node:
                    key = f"{original_key}_{counter}"
                    counter += 1
                
                parent_node[key] = {}
                parents.append((parent_node[key], level, key))
        
        return info
    
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
                with open(file_path, 'r', encoding='utf-8') as f:
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
            command = command.split()
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30
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

