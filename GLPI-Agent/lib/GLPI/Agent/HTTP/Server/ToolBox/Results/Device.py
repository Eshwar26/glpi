"""
GLPI Agent ToolBox Results Device Module

Represents a device discovered or inventoried by the agent.
"""

from typing import Dict, Any, Optional, List


class Device:
    """
    Represents a network device or computer.
    
    Stores device information from various sources like
    network discovery, inventory, and custom edits.
    """

    def __init__(self, **params):
        """
        Initialize a device.
        
        Args:
            **params: Device parameters including:
                - name: Device name
                - results: Results object (if being loaded as a source)
        """
        # Don't be loaded as a Results source
        if params.get('results'):
            return None
        
        self._name = params.get('name')
        self._files: Dict[str, Any] = {}
        self._active_sources: Dict[str, Any] = {}
        self._used_sources: Dict[str, bool] = {}
        self._noedit: Dict[str, bool] = {}
        self._edition: bool = False
        
        # Device fields
        self.source: str = ''
        self.ip: str = ''
        self.ips: str = ''
        self.tag: str = ''
        self.type: str = ''
        self.mac: str = ''

    def name(self) -> str:
        """
        Get device name.
        
        Returns:
            Device name
        """
        return self._name or ''

    def source(self) -> str:
        """Get device data source."""
        return getattr(self, 'source', '')

    def ip(self) -> str:
        """Get device IP address."""
        return getattr(self, 'ip', '')

    def ips(self) -> str:
        """Get device IP addresses list."""
        return getattr(self, 'ips', '')

    def tag(self) -> str:
        """Get device tag."""
        return getattr(self, 'tag', '')

    def type(self) -> str:
        """Get device type."""
        return getattr(self, 'type', '')

    def mac(self) -> str:
        """Get device MAC address."""
        return getattr(self, 'mac', '')

    def analyse_with(self, any_sources: List, type_sources: List):
        """
        Analyze device with given sources.
        
        Args:
            any_sources: Sources that apply to any file
            type_sources: Type-specific sources
        """
        files = set(self._files.keys())
        self._used_sources = {}
        
        # Sources are ordered to match files in the expected order
        for source in any_sources + type_sources:
            files_list = list(files)
            if not files_list:
                break
            
            for file in files_list:
                if not hasattr(source, 'analyze'):
                    continue
                
                fields = source.analyze(
                    self.name(), 
                    self._files.get(file), 
                    file
                )
                
                if not fields:
                    continue
                
                if not getattr(source, 'any', lambda: False)():
                    files.discard(file)
                
                self._active_sources[file] = source
                self._used_sources[source.name()] = True
                self.set_fields(fields)
                break

    def set_fields(self, fields: Dict[str, Any]):
        """
        Set multiple device fields.
        
        Args:
            fields: Dictionary of field names and values
        """
        for key, value in fields.items():
            # Don't override source if still an Edition
            if key == 'source' and self._edition:
                continue
            
            if isinstance(value, dict):
                # Essentially for noedit feature
                if not hasattr(self, key):
                    setattr(self, key, {})
                
                current = getattr(self, key)
                if isinstance(current, dict):
                    current.update(value)
            elif value is not None and len(str(value)) > 0:
                # Merge values in device
                setattr(self, key, value)
        
        # Has this device been edited with custom fields?
        if hasattr(self, 'source') and self.source == 'Edition':
            self._edition = True

    def set(self, field: str, value: Any):
        """
        Set a device field.
        
        Args:
            field: Field name
            value: Field value
        """
        setattr(self, field, value)
        
        # Defines if this device is an edition
        if field == 'source' and value == 'Edition':
            self._edition = True

    def delete(self, field: str):
        """
        Delete a device field.
        
        Args:
            field: Field name to delete
        """
        if hasattr(self, field):
            delattr(self, field)

    def get(self, field: str) -> str:
        """
        Get a device field value.
        
        Args:
            field: Field name
            
        Returns:
            Field value or empty string
        """
        value = getattr(self, field, '')
        return str(value) if value is not None and len(str(value)) > 0 else ''

    def noedit(self, field: Optional[str] = None) -> Any:
        """
        Check or get fields that cannot be edited.
        
        Args:
            field: Optional field name to check
            
        Returns:
            List of noedit fields if no field specified,
            True/False if field specified
        """
        if not self._noedit:
            return [] if field is None else False
        
        if field is None:
            return list(self._noedit.keys())
        
        # Don't edit if no edition permission has been set for a field
        return self._noedit.get(field, True)

    def dontedit(self, field: str):
        """
        Mark a field as non-editable.
        
        Args:
            field: Field name
        """
        self._noedit[field] = True

    def editfield(self, field: str):
        """
        Mark a field as editable.
        
        Args:
            field: Field name
        """
        self._noedit[field] = False

    def deduplicate(self, devices: Dict[str, 'Device']):
        """
        Deduplicate this device against existing devices.
        
        Args:
            devices: Dictionary of existing devices
        """
        found = None
        deviceid = self.get('deviceid')
        
        for device in devices.values():
            if device is self:
                continue
            
            # Merge data from netdiscovery & inventory when deviceid is stored
            if deviceid:
                thisdeviceid = device.get('deviceid')
                if thisdeviceid and thisdeviceid == deviceid:
                    found = device
                    break
            
            if not device.ip() or device.ip() != self.ip():
                continue
            
            found = device
            break
        
        if found:
            # Merge this device into found device
            for key in dir(self):
                if key.startswith('_') or callable(getattr(self, key)):
                    continue
                
                value = getattr(self, key, None)
                if value and not found.get(key):
                    found.set(key, value)
            
            return found
        
        return self

    def file(self, file: str, data: Any):
        """
        Add a file to the device.
        
        Args:
            file: File path
            data: File data
        """
        self._files[file] = data

    def files(self) -> List[str]:
        """
        Get list of device files.
        
        Returns:
            List of file paths
        """
        return list(self._files.keys())

