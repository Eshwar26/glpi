package GLPI::Agent::Task::Inventory::MacOS::Storages;

use strict;
use warnings;

use parent 'GLPI::Agent::Task::Inventory::Module';

use GLPI::Agent::Tools;
use GLPI::Agent::Tools::MacOS;

use constant    category    => "storage";

sub isEnabled {
    return 1;
}

sub doInventory {
    my (%params) = @_;

    my $inventory = $params{inventory};
    my $logger    = $params{logger};

    foreach my $storage ("""
GLPI Agent Task Inventory MacOS Storages Module

This module collects storage device information on macOS systems from
various sources: SATA, USB, FireWire, card readers, and disc burning devices.
"""

import re
import subprocess
from typing import Dict, Any, Optional, List


class Storages:
    """MacOS Storages inventory module."""
    
    @staticmethod
    def category():
        """Return the category for this inventory module."""
        return "storage"
    
    def is_enabled(self, **params):
        """
        Check if this module can run on the current system.
        
        Returns:
            bool: Always True for macOS systems.
        """
        return True
    
    def do_inventory(self, **params):
        """
        Perform the storage device inventory and add results to inventory.
        
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
        
        for storage in storages:
            inventory.add_entry(
                section='STORAGES',
                entry=storage
            )
    
    def _get_serial_ata_storages(self, **params):
        """
        Get SATA storage devices.
        
        Args:
            **params: Keyword arguments including:
                - logger: Optional logger object
        
        Returns:
            list: List of storage device dictionaries
        """
        logger = params.get('logger')
        
        # Note: This uses XML format in the Perl version with getSystemProfilerInfos
        # For simplicity, we parse text format here
        # A full implementation would parse XML for more accurate structured data
        
        lines = self._get_all_lines(
            command='/usr/sbin/system_profiler SPSerialATADataType',
            logger=logger
        )
        
        if not lines:
            return []
        
        storages = []
        # Simple text parsing (full implementation would use XML)
        # This is a placeholder - XML parsing would be more reliable
        
        return storages
    
    def _get_disc_burning_storages(self, **params):
        """
        Get disc burning devices (CD/DVD drives).
        
        Args:
            **params: Keyword arguments including:
                - logger: Optional logger object
        
        Returns:
            list: List of storage device dictionaries
        """
        logger = params.get('logger')
        
        lines = self._get_all_lines(
            command='/usr/sbin/system_profiler SPDiscBurningDataType',
            logger=logger
        )
        
        if not lines:
            return []
        
        storages = []
        # Placeholder for disc burning storage parsing
        
        return storages
    
    def _get_card_reader_storages(self, **params):
        """
        Get card reader devices.
        
        Args:
            **params: Keyword arguments including:
                - logger: Optional logger object
        
        Returns:
            list: List of storage device dictionaries
        """
        logger = params.get('logger')
        
        lines = self._get_all_lines(
            command='/usr/sbin/system_profiler SPCardReaderDataType',
            logger=logger
        )
        
        if not lines:
            return []
        
        storages = []
        # Placeholder for card reader parsing
        
        return storages
    
    def _get_usb_storages(self, **params):
        """
        Get USB storage devices.
        
        Args:
            **params: Keyword arguments including:
                - logger: Optional logger object
        
        Returns:
            list: List of storage device dictionaries
        """
        logger = params.get('logger')
        
        lines = self._get_all_lines(
            command='/usr/sbin/system_profiler SPUSBDataType',
            logger=logger
        )
        
        if not lines:
            return []
        
        storages = []
        current_device = None
        device_name = None
        
        for line in lines:
            # Look for USB storage devices in the output
            # This is a simplified parser - full implementation would use XML
            if ':' in line and not line.startswith(' ' * 10):
                if current_device and device_name:
                    # Check if it's a storage device
                    if self._is_usb_storage_device(device_name, current_device):
                        storage = self._process_usb_storage(device_name, current_device)
                        if storage:
                            storages.append(storage)
                
                device_name = line.split(':')[0].strip()
                current_device = {}
            elif current_device is not None and ':' in line:
                key, value = line.split(':', 1)
                current_device[key.strip()] = value.strip()
        
        # Process last device
        if current_device and device_name:
            if self._is_usb_storage_device(device_name, current_device):
                storage = self._process_usb_storage(device_name, current_device)
                if storage:
                    storages.append(storage)
        
        return storages
    
    def _get_firewire_storages(self, **params):
        """
        Get FireWire storage devices.
        
        Args:
            **params: Keyword arguments including:
                - logger: Optional logger object
        
        Returns:
            list: List of storage device dictionaries
        """
        logger = params.get('logger')
        
        lines = self._get_all_lines(
            command='/usr/sbin/system_profiler SPFireWireDataType',
            logger=logger
        )
        
        if not lines:
            return []
        
        storages = []
        # Placeholder for FireWire storage parsing
        
        return storages
    
    def _is_usb_storage_device(self, name, properties):
        """
        Check if a USB device is a storage device.
        
        Args:
            name: Device name
            properties: Device properties
        
        Returns:
            bool: True if it's a storage device
        """
        # Skip certain device types
        skip_patterns = [
            r'keyboard', r'controller', r'IR Receiver', r'built-in',
            r'hub', r'mouse', r'tablet', r'usb(?:\d+)?bus', r'Mass Storage Device'
        ]
        
        name_lower = name.lower()
        for pattern in skip_patterns:
            if re.search(pattern, name_lower, re.IGNORECASE):
                return False
        
        # Check if it has storage-related properties
        bsd_name = properties.get('BSD Name', '')
        if bsd_name and bsd_name.startswith('disk'):
            return True
        
        return False
    
    def _process_usb_storage(self, name, properties):
        """
        Process USB storage device properties into storage dict.
        
        Args:
            name: Device name
            properties: Device properties
        
        Returns:
            dict: Storage device dictionary
        """
        storage = {
            'NAME': properties.get('BSD Name', name),
            'TYPE': 'Disk drive',
            'INTERFACE': 'USB',
            'DESCRIPTION': name,
        }
        
        # Extract size
        size = properties.get('Capacity')
        if size:
            storage['DISKSIZE'] = self._get_canonical_size(size, 1024)
        
        # Extract model
        storage['MODEL'] = name
        
        # Extract serial number
        serial = properties.get('Serial Number')
        if serial:
            storage['SERIAL'] = serial
        
        # Extract manufacturer
        manufacturer = properties.get('Manufacturer')
        if manufacturer:
            storage['MANUFACTURER'] = self._get_canonical_manufacturer(manufacturer)
        
        # Sanitize and filter None values
        storage = self._sanitized_hash(storage)
        
        return storage if storage else None
    
    def _set_disk_size(self, hash_data, storage):
        """
        Set disk size in storage dictionary.
        
        Args:
            hash_data: Source data dictionary
            storage: Storage dictionary to update
        """
        size_bytes = hash_data.get('size_in_bytes')
        size_str = hash_data.get('size')
        
        if size_bytes:
            storage['DISKSIZE'] = self._get_canonical_size(f"{size_bytes} bytes", 1024)
        elif size_str:
            storage['DISKSIZE'] = self._get_canonical_size(size_str, 1024)
    
    def _get_canonical_size(self, size_str, base=1024):
        """
        Convert size string to MB.
        
        Args:
            size_str: Size string like "500 GB" or "1000000000 bytes"
            base: Base for conversion (1024 or 1000)
        
        Returns:
            int: Size in MB, or None
        """
        if not size_str:
            return None
        
        # Match number and unit
        match = re.match(r'([\d.]+)\s*([KMGTP]?B?|bytes?)', str(size_str), re.IGNORECASE)
        if not match:
            return None
        
        value = float(match.group(1))
        unit = match.group(2).upper()
        
        # Convert to MB
        if unit in ('B', 'BYTE', 'BYTES'):
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
    
    def _get_canonical_manufacturer(self, text):
        """
        Get canonical manufacturer name.
        
        This is a simplified version. The full implementation would use
        a manufacturer database.
        
        Args:
            text: Text to extract manufacturer from
        
        Returns:
            str: Canonical manufacturer name
        """
        if not text:
            return text
        
        # Simple manufacturer normalization
        known_manufacturers = {
            'apple': 'Apple',
            'samsung': 'Samsung',
            'sandisk': 'SanDisk',
            'kingston': 'Kingston',
            'western digital': 'Western Digital',
            'wd': 'Western Digital',
            'seagate': 'Seagate',
            'toshiba': 'Toshiba',
            'crucial': 'Crucial',
            'intel': 'Intel',
        }
        
        text_lower = text.lower()
        for key, value in known_manufacturers.items():
            if key in text_lower:
                return value
        
        return text
    
    def _trim_whitespace(self, text):
        """
        Trim leading and trailing whitespace.
        
        Args:
            text: String to trim
        
        Returns:
            str: Trimmed string
        """
        if not text:
            return text
        return text.strip()
    
    def _sanitized_hash(self, hash_dict):
        """
        Sanitize hash by trimming whitespace and removing None values.
        
        Args:
            hash_dict: Dictionary to sanitize
        
        Returns:
            dict: Sanitized dictionary
        """
        sanitized = {}
        for key, value in hash_dict.items():
            if value is not None:
                if isinstance(value, str):
                    value = self._trim_whitespace(value)
                    if value:  # Only add non-empty strings
                        sanitized[key] = value
                else:
                    sanitized[key] = value
        
        return sanitized
    
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
                timeout=60
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


        _getSerialATAStorages(logger => $logger),
        _getDiscBurningStorages(logger => $logger),
        _getCardReaderStorages(logger => $logger),
        _getUSBStorages(logger => $logger),
        _getFireWireStorages(logger => $logger)
    ) {
        $inventory->addEntry(
            section => 'STORAGES',
            entry   => $storage
        );
    }
}

sub _getSerialATAStorages {
    my (%params) = @_;

    my $infos = getSystemProfilerInfos(
        type   => 'SPSerialATADataType',
        format => 'xml',
        %params
    );
    return unless $infos->{storages};
    my @storages = ();
    foreach my $name (sort keys %{$infos->{storages}}) {
        my $hash = $infos->{storages}->{$name};
        next unless $hash->{partition_map_type} || $hash->{detachable_drive};
        next if $hash->{_name} =~ /controller/i;
        my $storage = {
            NAME         => $hash->{bsd_name} || $hash->{_name},
            MANUFACTURER => getCanonicalManufacturer($hash->{_name}),
            TYPE         => 'Disk drive',
            INTERFACE    => 'SATA',
            SERIAL       => $hash->{device_serial},
            MODEL        => $hash->{device_model} || $hash->{_name},
            FIRMWARE     => $hash->{device_revision},
            DESCRIPTION  => $hash->{_name}
        };

        _setDiskSize($hash, $storage);

        # Cleanup manufacturer from model
        $storage->{MODEL} =~ s/\s*$storage->{MANUFACTURER}\s*//i
            if $storage->{MODEL};

        push @storages, _sanitizedHash($storage);
    }

    return @storages;
}

sub _getDiscBurningStorages {
    my (%params) = @_;

    my @storages = ();
    my $infos = getSystemProfilerInfos(
        type   => 'SPDiscBurningDataType',
        format => 'xml',
        %params
    );
    return @storages unless $infos->{storages};

    foreach my $name (sort keys %{$infos->{storages}}) {
        my $hash = $infos->{storages}->{$name};
        my $storage = {
            NAME         => $hash->{bsd_name} || $hash->{_name},
            MANUFACTURER => getCanonicalManufacturer($hash->{manufacturer} || $hash->{_name}),
            TYPE         => 'Disk burning',
            INTERFACE    => $hash->{interconnect} && $hash->{interconnect} eq 'SERIAL-ATA' ? "SATA" : "ATAPI",
            MODEL        => $hash->{_name},
            FIRMWARE     => $hash->{firmware}
        };

        _setDiskSize($hash, $storage);

        # Cleanup manufacturer from model
        $storage->{MODEL} =~ s/\s*$storage->{MANUFACTURER}\s*//i
            if $storage->{MODEL};

        push @storages, _sanitizedHash($storage);
    }

    return @storages;
}

sub _getCardReaderStorages {
    my (%params) = @_;

    my $infos = getSystemProfilerInfos(
        type   => 'SPCardReaderDataType',
        format => 'xml',
        %params
    );
    return unless $infos->{storages};

    my @storages = ();
    foreach my $name (sort keys %{$infos->{storages}}) {
        my $hash = $infos->{storages}->{$name};
        next if ($hash->{iocontent} || $hash->{file_system} || $hash->{mount_point}) && !$hash->{partition_map_type};
        my $storage;
        if ($hash->{_name} eq 'spcardreader') {
            $storage = {
                NAME         => $hash->{bsd_name} || $hash->{_name},
                TYPE         => 'Card reader',
                DESCRIPTION  => $hash->{_name},
                SERIAL       => $hash->{spcardreader_serialnumber},
                MODEL        => $hash->{_name},
                FIRMWARE     => $hash->{'spcardreader_revision-id'},
                MANUFACTURER => $hash->{'spcardreader_vendor-id'}
            };
        } else {
            $storage = {
                NAME         => $hash->{bsd_name} || $hash->{_name},
                TYPE         => 'SD Card',
                DESCRIPTION  => $hash->{_name},
            };
            _setDiskSize($hash, $storage);
        }
        push @storages, _sanitizedHash($storage);
    }

    return @storages;
}

sub _getUSBStorages {
    my (%params) = @_;

    my $infos = getSystemProfilerInfos(
        type   => 'SPUSBDataType',
        format => 'xml',
        %params
    );
    return unless $infos->{storages};

    my @storages = ();
    foreach my $name (sort keys %{$infos->{storages}}) {
        my $hash = $infos->{storages}->{$name};
        unless ($hash->{bsn_name} && $hash->{bsd_name} =~ /^disk/) {
            next if $hash->{_name} eq 'Mass Storage Device';
            next if $hash->{_name} =~ /keyboard|controller|IR Receiver|built-in|hub|mouse|tablet|usb(?:\d+)?bus/i;
            next if ($hash->{'Built-in_Device'} && $hash->{'Built-in_Device'} eq 'Yes');
            next if ($hash->{iocontent} || $hash->{file_system} || $hash->{mount_point}) && !$hash->{partition_map_type};
        }
        my $storage = {
            NAME         => $hash->{bsd_name} || $hash->{_name},
            TYPE         => 'Disk drive',
            INTERFACE    => 'USB',
            DESCRIPTION  => $hash->{_name},
        };

        _setDiskSize($hash, $storage);

        my $extract = _getInfoExtract($hash);
        $storage->{MODEL} = $extract->{device_model} || $hash->{_name};
        $storage->{SERIAL} = $extract->{serial_num} if $extract->{serial_num};
        $storage->{FIRMWARE} = $extract->{bcd_device} if $extract->{bcd_device};
        $storage->{MANUFACTURER} = getCanonicalManufacturer($extract->{manufacturer})
            if $extract->{manufacturer};

        push @storages, _sanitizedHash($storage);
    }

    return @storages;
}

sub _setDiskSize {
    my ($hash, $storage) = @_;

    return unless $hash->{size_in_bytes} || $hash->{size};

    $storage->{DISKSIZE} = getCanonicalSize(
        $hash->{size_in_bytes} ? $hash->{size_in_bytes} . ' bytes' : $hash->{size},
        1024
    );
}

sub _getInfoExtract {
    my ($hash) = @_;

    my $extract = {};
    foreach my $key (keys(%{$hash})) {
        next unless defined($hash->{$key}) && $key =~ /^(?:\w_)?(serial_num|device_model|bcd_device|manufacturer|product_id)/;
        $extract->{$1} = $hash->{$key};
    }

    return $extract;
}

sub _getFireWireStorages {
    my (%params) = @_;

    my $infos = getSystemProfilerInfos(
        type   => 'SPFireWireDataType',
        format => 'xml',
        %params
    );
    return unless $infos->{storages};

    my @storages = ();
    foreach my $name (sort keys %{$infos->{storages}}) {
        my $hash = $infos->{storages}->{$name};
        next unless $hash->{partition_map_type};
        my $storage = {
            NAME         => $hash->{bsd_name} || $hash->{_name},
            TYPE         => 'Disk drive',
            INTERFACE    => '1394',
            DESCRIPTION  => $hash->{_name},
        };

        _setDiskSize($hash, $storage);

        my $extract = _getInfoExtract($hash);
        $storage->{MODEL} = $extract->{product_id} if $extract->{product_id};
        $storage->{SERIAL} = $extract->{serial_num} if $extract->{serial_num};
        $storage->{FIRMWARE} = $extract->{bcd_device} if $extract->{bcd_device};
        $storage->{MANUFACTURER} = getCanonicalManufacturer($extract->{manufacturer})
            if $extract->{manufacturer};

        push @storages, _sanitizedHash($storage);
    }

    return @storages;
}

sub _sanitizedHash {
    my ($hash) = @_;
    foreach my $key (keys(%{$hash})) {
        if (defined($hash->{$key})) {
            $hash->{$key} = trimWhitespace($hash->{$key});
        } else {
            delete $hash->{$key};
        }
    }
    return $hash;
}

1;
