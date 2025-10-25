"""
GLPI::Agent::Protocol::Inventory - Inventory GLPI Agent messages

This is a class to handle Inventory protocol messages.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from GLPI.Agent.Protocol.Message import ProtocolMessage


# Regular expressions for date/datetime validation
DATE_QR = re.compile(r'^[0-9]{4}-[0-9]{2}-[0-9]{2}$')
DATETIME_QR = re.compile(r'^[0-9]{4}-[0-9]{2}-[0-9]{2}[ |T][0-9]{2}:[0-9]{2}:[0-9]{2}(Z|[+|-][0-9]{2}:[0-9]{2}:[0-9]{2})?$')
DATEORDATETIME_QR = re.compile(r'^[0-9]{4}-[0-9]{2}-[0-9]{2}([ |T][0-9]{2}:[0-9]{2}:[0-9]{2}(Z|[+|-][0-9]{2}:[0-9]{2}:[0-9]{2})?)?$')

# List of values to normalize with integer/string/boolean/date/datetime or
# dateordatetime format before providing content for export
# Other constraints are also checked like lowercase, uppercase or required.
NORMALIZE = {
    'ACCESSLOG': {
        'required': ['LOGDATE'],
        'datetime': ['LOGDATE'],
    },
    'ANTIVIRUS': {
        'boolean': ['ENABLED', 'UPTODATE'],
        'date': ['EXPIRATION'],
    },
    'BATTERIES': {
        'date': ['DATE'],
        'integer': ['CAPACITY', 'REAL_CAPACITY', 'VOLTAGE'],
    },
    'BIOS': {
        'dateordatetime': ['BDATE'],
    },
    'CPUS': {
        'integer': ['CORE', 'CORECOUNT', 'EXTERNAL_CLOCK', 'SPEED', 'STEPPING', 'THREAD'],
        'string': ['MODEL', 'FAMILYNUMBER'],
    },
    'DATABASES_SERVICES': {
        'required': ['NAME', 'VERSION'],
        'integer': ['PORT', 'SIZE'],
        'boolean': ['IS_ACTIVE', 'IS_ONBACKUP'],
        'datetime': ['LAST_BOOT_DATE', 'LAST_BACKUP_DATE'],
    },
    'DATABASES_SERVICES/DATABASES': {
        'required': ['NAME'],
        'integer': ['SIZE'],
        'boolean': ['IS_ACTIVE', 'IS_ONBACKUP'],
        'datetime': ['CREATION_DATE', 'UPDATE_DATE', 'LAST_BACKUP_DATE'],
    },
    'DRIVES': {
        'boolean': ['SYSTEMDRIVE'],
        'integer': ['FREE', 'TOTAL'],
    },
    'ENVS': {
        'required': ['KEY', 'VAL'],
    },
    'FIREWALLS': {
        'required': ['STATUS'],
    },
    'HARDWARE': {
        'integer': ['MEMORY', 'SWAP'],
    },
    'LOCAL_GROUPS': {
        'required': ['ID', 'NAME'],
    },
    'LOCAL_USERS': {
        'required': ['ID'],
    },
    'PHYSICAL_VOLUMES': {
        'required': ['DEVICE', 'FORMAT', 'FREE', 'PV_PE_COUNT', 'PV_UUID', 'SIZE'],
        'integer': ['FREE', 'PE_SIZE', 'PV_PE_COUNT', 'SIZE'],
    },
    'VOLUME_GROUPS': {
        'required': ['FREE', 'LV_COUNT', 'PV_COUNT', 'SIZE', 'VG_EXTENT_SIZE', 'VG_NAME', 'VG_UUID'],
        'integer': ['FREE', 'LV_COUNT', 'PV_COUNT', 'SIZE'],
    },
    'LOGICAL_VOLUMES': {
        'required': ['LV_NAME', 'LV_UUID', 'SIZE'],
        'integer': ['SEG_COUNT', 'SIZE'],
    },
    'MEMORIES': {
        'integer': ['CAPACITY', 'NUMSLOTS'],
        'boolean': ['REMOVABLE'],
    },
    'MONITORS': {
        'string': ['DESCRIPTION', 'SERIAL', 'ALTSERIAL'],
    },
    'NETWORKS': {
        'required': ['DESCRIPTION'],
        'boolean': ['MANAGEMENT', 'VIRTUALDEV'],
        'integer': ['MTU'],
        'lowercase': ['STATUS'],
        'string': ['SPEED'],
    },
    'OPERATINGSYSTEM': {
        'datetime': ['BOOT_TIME', 'INSTALL_DATE'],
    },
    'OPERATINGSYSTEM/TIMEZONE': {
        'required': ['NAME', 'OFFSET'],
    },
    'PORTS': {
        'required': ['TYPE'],
    },
    'PRINTERS': {
        'required': ['NAME'],
        'boolean': ['NETWORK', 'SHARED'],
    },
    'PROCESSES': {
        'required': ['CMD', 'PID', 'USER'],
        'datetime': ['STARTED'],
        'integer': ['PID', 'VIRTUALMEMORY'],
    },
    'REMOTE_MGMT': {
        'required': ['ID', 'TYPE'],
        'string': ['ID'],
    },
    'SLOTS': {
        'required': ['DESCRIPTION', 'NAME'],
    },
    'SOFTWARES': {
        'required': ['NAME'],
        'boolean': ['NO_REMOVE'],
        'dateordatetime': ['INSTALLDATE'],
        'integer': ['FILESIZE'],
        'string': ['VERSION_MAJOR', 'VERSION_MINOR'],
    },
    'STORAGES': {
        'integer': ['DISKSIZE'],
        'uppercase': ['INTERFACE'],
    },
    'VIDEOS': {
        'integer': ['MEMORY'],
    },
    'VIRTUALMACHINES': {
        'required': ['NAME', 'VMTYPE'],
        'integer': ['MEMORY', 'VCPU'],
        'lowercase': ['STATUS', 'VMTYPE'],
        'pattern': [
            ['STATUS', r'^(running|blocked|idle|paused|shutdown|crashed|dying|off)$']
        ]
    },
    'LICENSEINFOS': {
        'boolean': ['TRIAL'],
        'datetime': ['ACTIVATION_DATE'],
    },
    'POWERSUPPLIES': {
        'boolean': ['HOTREPLACEABLE', 'PLUGGED'],
        'integer': ['POWER_MAX'],
    },
    'VERSIONPROVIDER': {
        'integer': ['ETIME'],
    },
}


class Inventory(ProtocolMessage):
    """
    Inventory protocol message handler.
    
    Handles inventory messages with normalization and validation.
    """
    
    def __init__(self, partial=None, **params):
        """
        Initialize inventory message.
        
        Args:
            partial (bool): Whether this is a partial inventory
            **params: Parameters including:
                - deviceid: Device identifier
                - action: Action type (default: 'inventory')
                - content: Inventory content
                - itemtype: Item type
                - message: Message content
                - logger: Logger instance
        """
        # Set supported params and default action
        params['supported_params'] = ['deviceid', 'action', 'content', 'itemtype', 'partial']
        params.setdefault('action', 'inventory')
        
        if partial is not None:
            params['partial'] = partial
        
        super().__init__(**params)
        
        # Only keep partial if it was explicitly set
        if partial is None and 'partial' in self._message:
            del self._message['partial']
        
        self._merge_content = None
    
    def merge_content(self, content):
        """
        Set content to be merged during conversion.
        
        Args:
            content (dict): Content to merge
        """
        if isinstance(content, dict):
            self._merge_content = content
    
    def _setup_standardization(self, version):
        """
        Adjust normalization rules based on server version.
        
        Args:
            version (str): Server version string
        """
        # Parse version setting default support to 10.0.0
        major, minor, rev, suffix = 10, 0, 0, ''
        if version:
            match = re.match(r'^(\d+)\.(\d+)\.(\d+)(?:-(.*))?$', version)
            if match:
                major = int(match.group(1))
                minor = int(match.group(2))
                rev = int(match.group(3))
                suffix = match.group(4) or ''
        
        if suffix == 'dev':
            if self.logger:
                self.logger.debug2(
                    "inventory format: server is a development version\n"
                    "Be sure to use latest GLPI Agent nightly build being aware your JSON inventory\n"
                    "may be rejected by server, and in that case, you probably just have to update the\n"
                    "server-side 'inventory.schema.json' file manually.\n"
                    "If this is not sufficient, please, can you open an issue on glpi-agent github project?"
                )
        elif suffix == 'beta':
            if self.logger:
                self.logger.debug2(
                    "inventory format: server is a beta version\n"
                    "Be sure to use latest GLPI Agent nightly build.\n"
                    "If the server rejects the inventory, please, report an issue on glpi-agent github project."
                )
            if major == 10 and not minor and not rev:
                # GLPI 10.0.0-beta supported specs
                if 'boolean' in NORMALIZE.get('MEMORIES', {}):
                    del NORMALIZE['MEMORIES']['boolean']
                    NORMALIZE['MEMORIES']['string'] = ['REMOVABLE']
    
    def normalize(self, version=None):
        """
        Parse content to normalize the inventory and prepare it for the expected JSON format.
        
        Args:
            version (str): Server version for compatibility adjustments
        """
        content = self.get('content')
        if not content:
            return
        
        # Fix NORMALIZE structure against server version
        self._setup_standardization(version)
        
        # Normalize to follow JSON specs
        for entrykey in NORMALIZE.keys():
            entries = []
            
            # Handle nested keys like "DATABASES_SERVICES/DATABASES"
            if '/' in entrykey:
                parent_key, child_key = entrykey.split('/', 1)
                if parent_key in content:
                    parent = content[parent_key]
                    if isinstance(parent, list):
                        entries = [item.get(child_key) for item in parent if child_key in item]
                    elif isinstance(parent, dict) and child_key in parent:
                        entries = [parent[child_key]]
            elif entrykey in content:
                entries = [content[entrykey]]
            
            for entry in entries:
                if not isinstance(entry, (dict, list)):
                    continue
                
                # Process all normalization types except 'required' first
                norm_types = [k for k in NORMALIZE[entrykey].keys() if k != 'required']
                
                for norm in norm_types:
                    for value in NORMALIZE[entrykey][norm]:
                        if isinstance(entry, list):
                            for item in entry:
                                self._norm(norm, item, value, entrykey)
                        else:
                            self._norm(norm, entry, value, entrykey)
                
                # Handle 'required' constraint
                if 'required' in NORMALIZE[entrykey]:
                    self._handle_required(content, entrykey, entry, NORMALIZE[entrykey]['required'])
        
        # Parse content and remove any undefined values
        _recursive_not_defined_cleanup(content)
        
        # Normalize main PARTIAL status
        self._norm('boolean', self.get(), 'partial', 'main')
        
        # Handle tag as a root property
        if 'ACCOUNTINFO' in content:
            infos = content.pop('ACCOUNTINFO')
            if isinstance(infos, list):
                for info in infos:
                    if info.get('KEYNAME') == 'TAG':
                        tag = info.get('KEYVALUE')
                        if tag:
                            self.merge(tag=tag)
                        break
        
        # Transform content to inventory_format
        self._transform()
    
    def _handle_required(self, content, entrykey, entry, required_fields):
        """Handle required field validation."""
        if isinstance(entry, list):
            # Check validity of each entry
            valid_entries = []
            for item in entry:
                missing = [field for field in required_fields if field not in item or item[field] is None]
                if missing:
                    if self.logger:
                        missing_str = ', '.join(missing) + (' value' if len(missing) == 1 else ' values')
                        dump_str = ','.join(f"{k}:{v}" for k, v in sorted(item.items()))
                        self.logger.debug(f"inventory format: Removing {entrykey} entry element with required missing {missing_str}: {dump_str}")
                else:
                    valid_entries.append(item)
            
            # Update content
            if '/' in entrykey:
                parent_key, child_key = entrykey.split('/', 1)
                if valid_entries:
                    # Update in parent
                    if isinstance(content[parent_key], list):
                        for parent_item in content[parent_key]:
                            if child_key in parent_item:
                                parent_item[child_key] = valid_entries
                    else:
                        content[parent_key][child_key] = valid_entries
                else:
                    # Remove empty entries
                    if isinstance(content[parent_key], list):
                        for parent_item in content[parent_key]:
                            parent_item.pop(child_key, None)
                    else:
                        content[parent_key].pop(child_key, None)
                    if self.logger:
                        self.logger.debug(f"inventory format: Removed all {entrykey} entry elements")
            else:
                if valid_entries:
                    content[entrykey] = valid_entries
                else:
                    content.pop(entrykey, None)
                    if self.logger:
                        self.logger.debug(f"inventory format: Removed all {entrykey} entry elements")
        else:
            # Single entry
            missing = [field for field in required_fields if field not in entry or entry[field] is None]
            if missing:
                if self.logger:
                    missing_str = ', '.join(missing) + (' value' if len(missing) == 1 else ' values')
                    dump_str = ','.join(f"{k}:{v}" for k, v in sorted(entry.items()))
                    self.logger.debug(f"inventory format: Removing {entrykey} entry with required missing {missing_str}: {dump_str}")
                
                if '/' in entrykey:
                    parent_key, child_key = entrykey.split('/', 1)
                    content[parent_key].pop(child_key, None)
                else:
                    content.pop(entrykey, None)
    
    def _norm(self, norm, entry, value, entrykey):
        """Apply normalization to an entry field."""
        # Pattern normalization is special
        if norm == 'pattern' and isinstance(value, list):
            key, pattern = value
            if key not in entry or entry[key] is None:
                return
            if not re.match(pattern, entry[key], re.IGNORECASE):
                if self.logger:
                    self.logger.debug(f"inventory format: Removing {entrykey} {key} value as not matching /{pattern}/ regexp: '{entry[key]}'")
                del entry[key]
            return
        
        if value not in entry or entry[value] is None:
            return
        
        if norm == 'integer':
            if isinstance(entry[value], str) and entry[value].isdigit():
                entry[value] = int(entry[value])
            elif isinstance(entry[value], int):
                pass  # Already integer
            else:
                if self.logger:
                    self.logger.debug(f"inventory format: Removing {entrykey} {value} value as not of {norm} type: '{entry[value]}'")
                del entry[value]
        elif norm == 'string':
            entry[value] = str(entry[value])
        elif norm == 'boolean':
            entry[value] = bool(entry[value])
        elif norm == 'lowercase':
            entry[value] = entry[value].lower()
        elif norm == 'uppercase':
            entry[value] = entry[value].upper()
        elif norm == 'date':
            if not DATE_QR.match(str(entry[value])):
                date = _canonical_date(entry[value])
                if date:
                    entry[value] = date
                else:
                    if self.logger:
                        self.logger.debug(f"inventory format: Removing {entrykey} {value} value as not of {norm} type: '{entry[value]}'")
                    del entry[value]
        elif norm == 'datetime':
            if not DATETIME_QR.match(str(entry[value])):
                dt = _canonical_datetime(entry[value])
                if dt:
                    entry[value] = dt
                else:
                    if self.logger:
                        self.logger.debug(f"inventory format: Removing {entrykey} {value} value as not of {norm} type: '{entry[value]}'")
                    del entry[value]
        elif norm == 'dateordatetime':
            if not DATEORDATETIME_QR.match(str(entry[value])):
                inverted = value == 'BDATE'
                dt = _canonical_dateordatetime(entry[value], inverted)
                if dt:
                    entry[value] = dt
                else:
                    if self.logger:
                        self.logger.debug(f"inventory format: Removing {entrykey} {value} value as not of {norm} type: '{entry[value]}'")
                    del entry[value]
    
    def converted(self):
        """Get converted message with merged content."""
        message = super().converted()
        if not message:
            return None
        
        content = message.get('content')
        if not content:
            return message
        
        # Merge content to support additional-content option
        merge = self._merge_content
        if merge:
            for key, value in merge.items():
                if key not in content or (not isinstance(value, (dict, list))):
                    content[key] = value
                elif isinstance(content[key], list) and isinstance(value, list):
                    content[key].extend(value)
                elif isinstance(content[key], dict) and isinstance(value, dict):
                    content[key].update(value)
                elif self.logger:
                    self.logger.debug(f"content merge: skipping '{key}' due to content type mismatch")
        
        return message
    
    def _transform(self):
        """Transform content to match expected inventory format."""
        content = self.get('content')
        if not content:
            return
        
        # Member property of local_groups has been renamed to members
        if 'LOCAL_GROUPS' in content and isinstance(content['LOCAL_GROUPS'], list):
            for group in content['LOCAL_GROUPS']:
                if 'MEMBER' in group:
                    group['MEMBERS'] = group.pop('MEMBER')
        
        # Installdate property of softwares has been renamed to install_date
        if 'SOFTWARES' in content and isinstance(content['SOFTWARES'], list):
            for software in content['SOFTWARES']:
                if 'INSTALLDATE' in software:
                    software['INSTALL_DATE'] = software.pop('INSTALLDATE')
        
        # Serialnumber property of storages has been renamed to serial
        if 'STORAGES' in content and isinstance(content['STORAGES'], list):
            for storage in content['STORAGES']:
                if 'SERIALNUMBER' in storage:
                    if self.logger and 'SERIAL' in storage and storage['SERIAL'] != storage['SERIALNUMBER']:
                        self.logger.debug2(f"Replacing {storage['SERIAL']} storage serial by {storage['SERIALNUMBER']}")
                    storage['SERIAL'] = storage.pop('SERIALNUMBER')
        
        # Firewall has been renamed to firewalls
        if 'FIREWALL' in content:
            firewalls = content.pop('FIREWALL')
            if isinstance(firewalls, list):
                content['FIREWALLS'] = firewalls
        
        # Macaddr property of networks has been renamed to mac
        if 'NETWORKS' in content and isinstance(content['NETWORKS'], list):
            for network in content['NETWORKS']:
                if 'MACADDR' in network:
                    network['MAC'] = network.pop('MACADDR')
        
        # Cleanup GLPI unsupported values
        if 'LICENSEINFOS' in content and isinstance(content['LICENSEINFOS'], list):
            for info in content['LICENSEINFOS']:
                info.pop('OEM', None)
        
        if 'VIDEOS' in content and isinstance(content['VIDEOS'], list):
            for video in content['VIDEOS']:
                video.pop('PCIID', None)
        
        content.pop('RUDDER', None)
        content.pop('REGISTRY', None)


def _recursive_not_defined_cleanup(entry):
    """Recursively remove None values from data structures."""
    if isinstance(entry, dict):
        keys_to_delete = [k for k, v in entry.items() if v is None]
        for key in keys_to_delete:
            del entry[key]
        for value in entry.values():
            _recursive_not_defined_cleanup(value)
    elif isinstance(entry, list):
        for item in entry:
            _recursive_not_defined_cleanup(item)


def _ymd(date_str):
    """Validate and return date in YYYY-MM-DD format."""
    if not date_str:
        return None
    
    match = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', date_str)
    if not match:
        return None
    
    year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
    
    try:
        dt = datetime(year, month, day)
        return dt.strftime('%Y-%m-%d')
    except ValueError:
        # Try inverting day and month in case the date is malformed
        try:
            dt = datetime(year, day, month)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            return None


def _canonical_date(date_str):
    """Convert various date formats to canonical YYYY-MM-DD."""
    if not date_str:
        return None
    
    # DD/MM/YYYY format
    match = re.match(r'^(\d{2})/(\d{2})/(\d{4})', str(date_str))
    if match:
        return _ymd(f"{match.group(3)}-{match.group(2)}-{match.group(1)}")
    
    # YYYY-MM-DD format
    match = re.match(r'^(\d{4}-\d{2}-\d{2})', str(date_str))
    if match:
        return _ymd(match.group(1))
    
    return None


def _canonical_datetime(datetime_str):
    """Convert various datetime formats to canonical YYYY-MM-DD HH:MM:SS."""
    if not datetime_str:
        return None
    
    # DD/MM/YYYY format (add time)
    match = re.match(r'^(\d{2})/(\d{2})/(\d{4})$', str(datetime_str))
    if match:
        ymd = _ymd(f"{match.group(3)}-{match.group(2)}-{match.group(1)}")
        if ymd:
            return f"{ymd} 00:00:00"
    
    # YYYY-MM-DD HH:MM format (add seconds)
    match = re.match(r'^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})$', str(datetime_str))
    if match:
        ymd = _ymd(match.group(1))
        if ymd:
            return f"{ymd} {match.group(2)}:00"
    
    return None


def _canonical_dateordatetime(date_str, inverted_month_and_day=False):
    """Convert date format to canonical, optionally inverting month/day."""
    if not date_str:
        return None
    
    # DD/MM/YYYY or MM/DD/YYYY format
    match = re.match(r'^(\d{2})/(\d{2})/(\d{4})$', str(date_str))
    if match:
        if inverted_month_and_day:
            return _ymd(f"{match.group(3)}-{match.group(1)}-{match.group(2)}")
        else:
            return _ymd(f"{match.group(3)}-{match.group(2)}-{match.group(1)}")
    
    return None
