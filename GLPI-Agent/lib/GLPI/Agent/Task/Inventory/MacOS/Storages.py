"""
GLPI Agent Task Inventory MacOS Storages Module

This module collects storage device information on macOS systems from
various sources: SATA, USB, FireWire, card readers, and disc burning devices.

This is a complete Python conversion of the Perl module:
GLPI::Agent::Task::Inventory::MacOS::Storages
"""

import re
import subprocess
import plistlib
from typing import Dict, Any, Optional, List, Union


class Storages:
    """MacOS Storages inventory module."""
    
    @staticmethod
    def category() -> str:
        """
        Return the category for this inventory module.
        
        Returns:
            str: The category identifier "storage"
        """
        return "storage"
    
    def is_enabled(self, **params) -> bool:
        """
        Check if this module can run on the current system.
        
        Args:
            **params: Keyword arguments (unused but maintained for interface compatibility)
        
        Returns:
            bool: Always True for macOS systems.
        """
        return True
    
    def do_inventory(self, **params):
        """
        Perform the storage device inventory and add results to inventory.
        
        This method collects storage information from multiple sources:
        - Serial ATA (SATA) devices
        - Disc burning devices (CD/DVD drives)
        - Card readers
        - USB storage devices
        - FireWire (IEEE 1394) devices
        
        Args:
            **params: Keyword arguments including:
                - inventory: The inventory object to add entries to
                - logger: Optional logger object for logging
        """
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        # Collect storage devices from all sources
        storages = []
        storages.extend(self._get_serial_ata_storages(logger=logger))
        storages.extend(self._get_disc_burning_storages(logger=logger))
        storages.extend(self._get_card_reader_storages(logger=logger))
        storages.extend(self._get_usb_storages(logger=logger))
        storages.extend(self._get_firewire_storages(logger=logger))
        
        # Add each storage device to the inventory
        for storage in storages:
            if inventory:
                inventory.add_entry(
                    section='STORAGES',
                    entry=storage
                )
    
    def _get_serial_ata_storages(self, **params) -> List[Dict[str, Any]]:
        """
        Get SATA storage devices using system_profiler.
        
        This method retrieves information about SATA-connected storage devices
        including internal hard drives and SSDs.
        
        Args:
            **params: Keyword arguments including:
                - logger: Optional logger object
        
        Returns:
            list: List of storage device dictionaries with keys:
                - NAME: Device BSD name or display name
                - MANUFACTURER: Device manufacturer
                - TYPE: "Disk drive"
                - INTERFACE: "SATA"
                - SERIAL: Device serial number
                - MODEL: Device model name
                - FIRMWARE: Firmware revision
                - DESCRIPTION: Device description
                - DISKSIZE: Disk size in MB (if available)
        """
        logger = params.get('logger')
        
        infos = self._get_system_profiler_infos(
            profile_type='SPSerialATADataType',
            format_type='xml',
            logger=logger
        )
        
        if not infos or 'storages' not in infos:
            return []
        
        storages = []
        for name in sorted(infos['storages'].keys()):
            hash_data = infos['storages'][name]
            
            # Skip non-storage devices (controllers)
            if not (hash_data.get('partition_map_type') or hash_data.get('detachable_drive')):
                continue
            if hash_data.get('_name') and re.search(r'controller', hash_data['_name'], re.IGNORECASE):
                continue
            
            storage = {
                'NAME': hash_data.get('bsd_name') or hash_data.get('_name'),
                'MANUFACTURER': self._get_canonical_manufacturer(hash_data.get('_name', '')),
                'TYPE': 'Disk drive',
                'INTERFACE': 'SATA',
                'SERIAL': hash_data.get('device_serial'),
                'MODEL': hash_data.get('device_model') or hash_data.get('_name'),
                'FIRMWARE': hash_data.get('device_revision'),
                'DESCRIPTION': hash_data.get('_name')
            }
            
            # Set disk size
            self._set_disk_size(hash_data, storage)
            
            # Cleanup manufacturer from model name
            if storage.get('MODEL') and storage.get('MANUFACTURER'):
                storage['MODEL'] = re.sub(
                    r'\s*' + re.escape(storage['MANUFACTURER']) + r'\s*',
                    '',
                    storage['MODEL'],
                    flags=re.IGNORECASE
                )
            
            storages.append(self._sanitized_hash(storage))
        
        return storages
    
    def _get_disc_burning_storages(self, **params) -> List[Dict[str, Any]]:
        """
        Get disc burning devices (CD/DVD/Blu-ray drives).
        
        Args:
            **params: Keyword arguments including:
                - logger: Optional logger object
        
        Returns:
            list: List of storage device dictionaries with keys:
                - NAME: Device BSD name or display name
                - MANUFACTURER: Device manufacturer
                - TYPE: "Disk burning"
                - INTERFACE: "SATA" or "ATAPI" depending on interconnect
                - MODEL: Device model name
                - FIRMWARE: Firmware version
                - DISKSIZE: Disk size in MB (if available)
        """
        logger = params.get('logger')
        
        infos = self._get_system_profiler_infos(
            profile_type='SPDiscBurningDataType',
            format_type='xml',
            logger=logger
        )
        
        if not infos or 'storages' not in infos:
            return []
        
        storages = []
        for name in sorted(infos['storages'].keys()):
            hash_data = infos['storages'][name]
            
            # Determine interface type
            interface = 'ATAPI'
            if hash_data.get('interconnect') and hash_data['interconnect'] == 'SERIAL-ATA':
                interface = 'SATA'
            
            storage = {
                'NAME': hash_data.get('bsd_name') or hash_data.get('_name'),
                'MANUFACTURER': self._get_canonical_manufacturer(
                    hash_data.get('manufacturer') or hash_data.get('_name', '')
                ),
                'TYPE': 'Disk burning',
                'INTERFACE': interface,
                'MODEL': hash_data.get('_name'),
                'FIRMWARE': hash_data.get('firmware')
            }
            
            # Set disk size
            self._set_disk_size(hash_data, storage)
            
            # Cleanup manufacturer from model name
            if storage.get('MODEL') and storage.get('MANUFACTURER'):
                storage['MODEL'] = re.sub(
                    r'\s*' + re.escape(storage['MANUFACTURER']) + r'\s*',
                    '',
                    storage['MODEL'],
                    flags=re.IGNORECASE
                )
            
            storages.append(self._sanitized_hash(storage))
        
        return storages
    
    def _get_card_reader_storages(self, **params) -> List[Dict[str, Any]]:
        """
        Get card reader devices and SD cards.
        
        Args:
            **params: Keyword arguments including:
                - logger: Optional logger object
        
        Returns:
            list: List of storage device dictionaries with keys:
                - NAME: Device BSD name or display name
                - TYPE: "Card reader" or "SD Card"
                - DESCRIPTION: Device description
                - SERIAL: Serial number (for card readers)
                - MODEL: Device model
                - FIRMWARE: Firmware revision (for card readers)
                - MANUFACTURER: Manufacturer/vendor ID (for card readers)
                - DISKSIZE: Disk size in MB (for SD cards)
        """
        logger = params.get('logger')
        
        infos = self._get_system_profiler_infos(
            profile_type='SPCardReaderDataType',
            format_type='xml',
            logger=logger
        )
        
        if not infos or 'storages' not in infos:
            return []
        
        storages = []
        for name in sorted(infos['storages'].keys()):
            hash_data = infos['storages'][name]
            
            # Skip mounted volumes that aren't partitioned storage
            has_content = (hash_data.get('iocontent') or 
                          hash_data.get('file_system') or 
                          hash_data.get('mount_point'))
            if has_content and not hash_data.get('partition_map_type'):
                continue
            
            # Determine if this is the card reader itself or an inserted card
            if hash_data.get('_name') == 'spcardreader':
                storage = {
                    'NAME': hash_data.get('bsd_name') or hash_data.get('_name'),
                    'TYPE': 'Card reader',
                    'DESCRIPTION': hash_data.get('_name'),
                    'SERIAL': hash_data.get('spcardreader_serialnumber'),
                    'MODEL': hash_data.get('_name'),
                    'FIRMWARE': hash_data.get('spcardreader_revision-id'),
                    'MANUFACTURER': hash_data.get('spcardreader_vendor-id')
                }
            else:
                # This is an SD card or similar media
                storage = {
                    'NAME': hash_data.get('bsd_name') or hash_data.get('_name'),
                    'TYPE': 'SD Card',
                    'DESCRIPTION': hash_data.get('_name')
                }
                self._set_disk_size(hash_data, storage)
            
            storages.append(self._sanitized_hash(storage))
        
        return storages
    
    def _get_usb_storages(self, **params) -> List[Dict[str, Any]]:
        """
        Get USB storage devices including external hard drives, flash drives, etc.
        
        Args:
            **params: Keyword arguments including:
                - logger: Optional logger object
        
        Returns:
            list: List of storage device dictionaries with keys:
                - NAME: Device BSD name or display name
                - TYPE: "Disk drive"
                - INTERFACE: "USB"
                - DESCRIPTION: Device description
                - MODEL: Device model
                - SERIAL: Serial number (if available)
                - FIRMWARE: BCD device version (if available)
                - MANUFACTURER: Device manufacturer (if available)
                - DISKSIZE: Disk size in MB (if available)
        """
        logger = params.get('logger')
        
        infos = self._get_system_profiler_infos(
            profile_type='SPUSBDataType',
            format_type='xml',
            logger=logger
        )
        
        if not infos or 'storages' not in infos:
            return []
        
        storages = []
        for name in sorted(infos['storages'].keys()):
            hash_data = infos['storages'][name]
            
            # Filter out non-storage USB devices
            has_bsd_disk = hash_data.get('bsd_name') and hash_data['bsd_name'].startswith('disk')
            
            if not has_bsd_disk:
                # Skip various non-storage devices
                if hash_data.get('_name') == 'Mass Storage Device':
                    continue
                if hash_data.get('_name') and re.search(
                    r'keyboard|controller|IR Receiver|built-in|hub|mouse|tablet|usb(?:\d+)?bus',
                    hash_data['_name'],
                    re.IGNORECASE
                ):
                    continue
                if hash_data.get('Built-in_Device') == 'Yes':
                    continue
                
                # Skip mounted volumes that aren't partitioned storage
                has_content = (hash_data.get('iocontent') or 
                              hash_data.get('file_system') or 
                              hash_data.get('mount_point'))
                if has_content and not hash_data.get('partition_map_type'):
                    continue
            
            storage = {
                'NAME': hash_data.get('bsd_name') or hash_data.get('_name'),
                'TYPE': 'Disk drive',
                'INTERFACE': 'USB',
                'DESCRIPTION': hash_data.get('_name')
            }
            
            # Set disk size
            self._set_disk_size(hash_data, storage)
            
            # Extract additional information
            extract = self._get_info_extract(hash_data)
            storage['MODEL'] = extract.get('device_model') or hash_data.get('_name')
            
            if extract.get('serial_num'):
                storage['SERIAL'] = extract['serial_num']
            if extract.get('bcd_device'):
                storage['FIRMWARE'] = extract['bcd_device']
            if extract.get('manufacturer'):
                storage['MANUFACTURER'] = self._get_canonical_manufacturer(extract['manufacturer'])
            
            storages.append(self._sanitized_hash(storage))
        
        return storages
    
    def _get_firewire_storages(self, **params) -> List[Dict[str, Any]]:
        """
        Get FireWire (IEEE 1394) storage devices.
        
        Args:
            **params: Keyword arguments including:
                - logger: Optional logger object
        
        Returns:
            list: List of storage device dictionaries with keys:
                - NAME: Device BSD name or display name
                - TYPE: "Disk drive"
                - INTERFACE: "1394" (FireWire)
                - DESCRIPTION: Device description
                - MODEL: Product ID (if available)
                - SERIAL: Serial number (if available)
                - FIRMWARE: BCD device version (if available)
                - MANUFACTURER: Device manufacturer (if available)
                - DISKSIZE: Disk size in MB (if available)
        """
        logger = params.get('logger')
        
        infos = self._get_system_profiler_infos(
            profile_type='SPFireWireDataType',
            format_type='xml',
            logger=logger
        )
        
        if not infos or 'storages' not in infos:
            return []
        
        storages = []
        for name in sorted(infos['storages'].keys()):
            hash_data = infos['storages'][name]
            
            # Only process partitioned storage devices
            if not hash_data.get('partition_map_type'):
                continue
            
            storage = {
                'NAME': hash_data.get('bsd_name') or hash_data.get('_name'),
                'TYPE': 'Disk drive',
                'INTERFACE': '1394',
                'DESCRIPTION': hash_data.get('_name')
            }
            
            # Set disk size
            self._set_disk_size(hash_data, storage)
            
            # Extract additional information
            extract = self._get_info_extract(hash_data)
            
            if extract.get('product_id'):
                storage['MODEL'] = extract['product_id']
            if extract.get('serial_num'):
                storage['SERIAL'] = extract['serial_num']
            if extract.get('bcd_device'):
                storage['FIRMWARE'] = extract['bcd_device']
            if extract.get('manufacturer'):
                storage['MANUFACTURER'] = self._get_canonical_manufacturer(extract['manufacturer'])
            
            storages.append(self._sanitized_hash(storage))
        
        return storages
    
    def _set_disk_size(self, hash_data: Dict[str, Any], storage: Dict[str, Any]):
        """
        Set the DISKSIZE field in the storage dictionary based on size information.
        
        Args:
            hash_data: Dictionary containing device information with size_in_bytes or size
            storage: Storage dictionary to update with DISKSIZE field
        """
        if not (hash_data.get('size_in_bytes') or hash_data.get('size')):
            return
        
        if hash_data.get('size_in_bytes'):
            size_str = f"{hash_data['size_in_bytes']} bytes"
        else:
            size_str = hash_data['size']
        
        storage['DISKSIZE'] = self._get_canonical_size(size_str, 1024)
    
    def _get_info_extract(self, hash_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant information fields from device hash.
        
        This method searches for fields matching patterns for serial numbers,
        device models, BCD device versions, manufacturers, and product IDs.
        It handles both prefixed and non-prefixed field names.
        
        Args:
            hash_data: Dictionary containing device information
        
        Returns:
            dict: Extracted information with standardized keys:
                - serial_num: Device serial number
                - device_model: Device model name
                - bcd_device: BCD device version
                - manufacturer: Manufacturer name
                - product_id: Product identifier
        """
        extract = {}
        pattern = re.compile(r'^(?:\w_)?(serial_num|device_model|bcd_device|manufacturer|product_id)$')
        
        for key, value in hash_data.items():
            if value is not None:
                match = pattern.match(key)
                if match:
                    extract[match.group(1)] = value
        
        return extract
    
    def _sanitized_hash(self, hash_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize a hash by trimming whitespace and removing None values.
        
        Args:
            hash_data: Dictionary to sanitize
        
        Returns:
            dict: Sanitized dictionary with trimmed strings and no None values
        """
        sanitized = {}
        for key, value in hash_data.items():
            if value is not None:
                # Trim whitespace if it's a string
                if isinstance(value, str):
                    sanitized[key] = self._trim_whitespace(value)
                else:
                    sanitized[key] = value
        return sanitized
    
    def _trim_whitespace(self, text: str) -> str:
        """
        Trim leading and trailing whitespace from a string.
        
        Args:
            text: String to trim
        
        Returns:
            str: Trimmed string
        """
        return text.strip() if text else text
    
    def _get_canonical_manufacturer(self, name: str) -> Optional[str]:
        """
        Extract and normalize manufacturer name from device name or string.
        
        This method attempts to identify common manufacturer names and patterns
        in device strings and return a canonical manufacturer name.
        
        Args:
            name: Device name or string that may contain manufacturer info
        
        Returns:
            str or None: Canonical manufacturer name or None if not identified
        """
        if not name:
            return None
        
        # Common manufacturer mappings
        manufacturers = {
            r'\bapple\b': 'Apple',
            r'\bsamsung\b': 'Samsung',
            r'\bseagate\b': 'Seagate',
            r'\bwestern digital\b|\bwd\b': 'Western Digital',
            r'\btoshiba\b': 'Toshiba',
            r'\bhitachi\b': 'Hitachi',
            r'\bhgst\b': 'HGST',
            r'\bcorsair\b': 'Corsair',
            r'\bkingston\b': 'Kingston',
            r'\bcrucial\b': 'Crucial',
            r'\bsandisk\b': 'SanDisk',
            r'\bintel\b': 'Intel',
            r'\bmicron\b': 'Micron',
            r'\bsk hynix\b': 'SK Hynix',
            r'\btranscend\b': 'Transcend',
            r'\bpny\b': 'PNY',
            r'\blg\b': 'LG',
            r'\bsony\b': 'Sony',
            r'\bpioneer\b': 'Pioneer',
            r'\basus\b': 'ASUS',
            r'\bmaxtor\b': 'Maxtor',
            r'\bquantum\b': 'Quantum',
            r'\biomega\b': 'Iomega',
            r'\blacie\b': 'LaCie',
        }
        
        name_lower = name.lower()
        for pattern, manufacturer in manufacturers.items():
            if re.search(pattern, name_lower):
                return manufacturer
        
        # Try to extract first word as potential manufacturer
        words = name.split()
        if words and len(words[0]) > 2:
            return words[0].strip()
        
        return None
    
    def _get_canonical_size(self, size_str: str, base: int = 1024) -> Optional[int]:
        """
        Convert a size string to canonical size in MB.
        
        This method parses size strings like "500 GB", "1 TB", "1000000000 bytes"
        and converts them to megabytes using the specified base (1024 or 1000).
        
        Args:
            size_str: Size string to parse (e.g., "500 GB", "1 TB", "1000000000 bytes")
            base: Base for conversion (1024 for binary, 1000 for decimal)
        
        Returns:
            int or None: Size in MB, or None if parsing fails
        """
        if not size_str:
            return None
        
        # Parse size string
        size_str = size_str.strip().upper()
        
        # Extract number and unit
        match = re.match(r'([\d.]+)\s*(\w+)?', size_str)
        if not match:
            return None
        
        size_value = float(match.group(1))
        unit = match.group(2) if match.group(2) else 'BYTES'
        
        # Convert to bytes first
        unit_multipliers = {
            'BYTES': 1,
            'BYTE': 1,
            'B': 1,
            'KB': base,
            'MB': base ** 2,
            'GB': base ** 3,
            'TB': base ** 4,
            'PB': base ** 5,
            'KIB': 1024,
            'MIB': 1024 ** 2,
            'GIB': 1024 ** 3,
            'TIB': 1024 ** 4,
            'PIB': 1024 ** 5,
        }
        
        multiplier = unit_multipliers.get(unit, 1)
        size_bytes = size_value * multiplier
        
        # Convert to MB
        size_mb = int(size_bytes / (base ** 2))
        
        return size_mb if size_mb > 0 else None
    
    def _get_system_profiler_infos(self, profile_type: str, format_type: str = 'xml', 
                                   logger=None) -> Optional[Dict[str, Any]]:
        """
        Get system profiler information for a specific data type.
        
        This method executes the system_profiler command and parses the XML output
        to extract storage device information.
        
        Args:
            profile_type: Type of profile to query (e.g., 'SPSerialATADataType')
            format_type: Output format ('xml' or 'text')
            logger: Optional logger object for logging
        
        Returns:
            dict or None: Dictionary containing parsed storage information with structure:
                {
                    'storages': {
                        'device_name': {
                            'property': 'value',
                            ...
                        },
                        ...
                    }
                }
        """
        try:
            # Build command
            command = ['/usr/sbin/system_profiler', profile_type]
            if format_type == 'xml':
                command.append('-xml')
            
            # Execute command
            result = subprocess.run(
                command,
                capture_output=True,
                text=False if format_type == 'xml' else True,
                timeout=30
            )
            
            if result.returncode != 0:
                if logger:
                    logger.error(f"system_profiler failed with return code {result.returncode}")
                return None
            
            # Parse XML output
            if format_type == 'xml':
                return self._parse_system_profiler_xml(result.stdout, profile_type, logger)
            else:
                # Text format parsing (less reliable, XML is preferred)
                return self._parse_system_profiler_text(result.stdout, logger)
        
        except subprocess.TimeoutExpired:
            if logger:
                logger.error(f"Command timed out: system_profiler {profile_type}")
            return None
        except FileNotFoundError:
            if logger:
                logger.error("system_profiler command not found")
            return None
        except Exception as e:
            if logger:
                logger.error(f"Error executing system_profiler: {e}")
            return None
    
    def _parse_system_profiler_xml(self, xml_data: bytes, profile_type: str, 
                                   logger=None) -> Optional[Dict[str, Any]]:
        """
        Parse XML output from system_profiler.
        
        This method parses the plist XML format returned by system_profiler
        and extracts storage device information into a structured dictionary.
        
        Args:
            xml_data: Raw XML data from system_profiler
            profile_type: Type of profile being parsed
            logger: Optional logger object
        
        Returns:
            dict or None: Parsed storage information
        """
        try:
            # Parse plist XML
            plist = plistlib.loads(xml_data)
            
            if not plist or not isinstance(plist, list):
                return None
            
            # Extract storage information
            storages = {}
            
            # The structure varies by profile type, but generally:
            # plist is a list with one element containing '_items'
            for item in plist:
                if '_items' in item:
                    self._extract_items_recursive(item['_items'], storages, logger)
            
            return {'storages': storages} if storages else None
        
        except Exception as e:
            if logger:
                logger.error(f"Error parsing XML: {e}")
            return None
    
    def _extract_items_recursive(self, items: List[Dict], storages: Dict, 
                                logger=None, parent_name: str = ''):
        """
        Recursively extract storage items from system_profiler plist structure.
        
        Args:
            items: List of item dictionaries from plist
            storages: Dictionary to populate with storage devices
            logger: Optional logger object
            parent_name: Name of parent item (for nested structures)
        """
        if not isinstance(items, list):
            return
        
        for item in items:
            if not isinstance(item, dict):
                continue
            
            # Get item name
            item_name = item.get('_name', '')
            
            # Create a flattened copy of the item
            storage_data = {'_name': item_name}
            
            # Copy all non-nested properties
            for key, value in item.items():
                if key != '_items' and not isinstance(value, (list, dict)):
                    storage_data[key] = value
                elif key != '_items' and isinstance(value, dict):
                    # Flatten nested dictionaries
                    for sub_key, sub_value in value.items():
                        if not isinstance(sub_value, (list, dict)):
                            storage_data[f"{key}_{sub_key}"] = sub_value
            
            # Store this item
            if item_name:
                storages[item_name] = storage_data
            
            # Recursively process nested items
            if '_items' in item:
                self._extract_items_recursive(item['_items'], storages, logger, item_name)
    
    def _parse_system_profiler_text(self, text_data: str, logger=None) -> Optional[Dict[str, Any]]:
        """
        Parse text output from system_profiler (fallback method).
        
        Note: XML parsing is more reliable. This is a simplified fallback.
        
        Args:
            text_data: Text output from system_profiler
            logger: Optional logger object
        
        Returns:
            dict or None: Parsed storage information
        """
        # This is a simplified text parser
        # In practice, XML format should always be preferred
        lines = text_data.split('\n') if text_data else []
        
        storages = {}
        current_device = None
        current_name = None
        
        for line in lines:
            # Basic parsing logic
            if line and not line.startswith(' ' * 4):
                # New top-level item
                if ':' in line:
                    if current_device and current_name:
                        storages[current_name] = current_device
                    current_name = line.split(':')[0].strip()
                    current_device = {'_name': current_name}
            elif current_device is not None and ':' in line:
                # Property of current device
                parts = line.split(':', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    current_device[key] = value
        
        # Add last device
        if current_device and current_name:
            storages[current_name] = current_device
        
        return {'storages': storages} if storages else None


# Module-level functions for compatibility with the original Perl interface

def category():
    """Return the category for this module."""
    return Storages.category()


def is_enabled(**params):
    """Check if this module is enabled."""
    instance = Storages()
    return instance.is_enabled(**params)


def do_inventory(**params):
    """Perform the inventory."""
    instance = Storages()
    return instance.do_inventory(**params)