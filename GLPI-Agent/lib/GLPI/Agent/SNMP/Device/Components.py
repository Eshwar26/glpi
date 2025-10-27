import re
from typing import Dict, List, Any, Optional

# Assuming GLPIAgentTools and GLPIAgentToolsSNMP are available
from glpi_agent_tools import getCanonicalConstant, getCanonicalString, trimWhitespace, getCanonicalMacAddress, getCanonicalSerialNumber, getCanonicalCount
from glpi_agent_tools_snmp import *

# See ENTITY-MIB
ENT_PHYSICAL_ENTRY = '.1.3.6.1.2.1.47.1.1.1.1'

# See Dell-Vendor-MIB
PRODUCT_IDENTIFICATION_SERIAL_NUMBER = '.1.3.6.1.4.1.674.10895.3000.1.2.100.8.1.2'

# components interface variables
PHYSICAL_COMPONENTS_VARIABLES = {
    'INDEX': {  # entPhysicalIndex
        'suffix': '1',
        'type': 'constant'
    },
    'NAME': {  # entPhysicalName
        'suffix': '7',
        'type': 'string'
    },
    'DESCRIPTION': {  # entPhysicalDescr
        'suffix': '2',
        'type': 'string'
    },
    'SERIAL': {  # entPhysicalSerialNum
        'suffix': '11',
        'type': 'string'
    },
    'MODEL': {  # entPhysicalModelName
        'suffix': '13',
        'type': 'string'
    },
    'TYPE': {  # entPhysicalClass
        'suffix': '5',
        'type': 'type',
        'types': {
            'other(1)': 'other',
            1: 'other',
            'unknown(2)': 'unknown',
            2: 'unknown',
            'chassis(3)': 'chassis',
            3: 'chassis',
            'backplane(4)': 'backplane',
            4: 'backplane',
            'container(5)': 'container',
            5: 'container',
            'powerSupply(6)': 'powerSupply',
            6: 'powerSupply',
            'fan(7)': 'fan',
            7: 'fan',
            'sensor(8)': 'sensor',
            8: 'sensor',
            'module(9)': 'module',
            9: 'module',
            'port(10)': 'port',
            10: 'port',
            'stack(11)': 'stack',
            11: 'stack',
            'cpu(12)': 'cpu',
            12: 'cpu'
        }
    },
    'FRU': {  # entPhysicalIsFRU
        'suffix': '16',
        'type': 'constant'
    },
    'MANUFACTURER': {  # entPhysicalMfgName
        'suffix': '12',
        'type': 'string'
    },
    'FIRMWARE': {  # entPhysicalFirmwareRev
        'suffix': '9',
        'type': 'string'
    },
    'REVISION': {  # entPhysicalHardwareRev
        'suffix': '8',
        'type': 'string'
    },
    'VERSION': {  # entPhysicalSoftwareRev
        'suffix': '10',
        'type': 'string'
    },
    'CONTAINEDININDEX': {  # entPhysicalContainedIn
        'suffix': '4',
        'type': 'constant'
    },
    'MAC': {
        'type': 'mac'
    },
    'IP': {
        'type': 'string'
    },
}


class GLPIAgentSNMPDeviceComponents:
    """
    GLPI agent SNMP device components

    Class to help handle components method for snmp device inventory
    """

    def __new__(cls, **params):
        device = params.get('device')
        if not device:
            return None

        self = super().__new__(cls)
        self.device = device
        self._components = []

        # First walk all entPhysicalEntry entries
        walk = device.walk(ENT_PHYSICAL_ENTRY)
        if not walk:
            return None
        if not walk:
            return None

        # Parse suffixes to only keep what we really need from the walk
        supported = {}
        for key in PHYSICAL_COMPONENTS_VARIABLES:
            if 'suffix' in PHYSICAL_COMPONENTS_VARIABLES[key]:
                supported[PHYSICAL_COMPONENTS_VARIABLES[key]['suffix']] = key
        supported_suffixes = sorted(supported.keys(), key=int)
        supported_str = '|'.join(supported_suffixes)
        supported_re = re.compile(rf'^({supported_str})\.(.+)$')
        walks = {}
        for oidleaf in walk:
            match = supported_re.match(oidleaf)
            if match:
                node, suffix = match.groups()
                walks.setdefault(supported[node], {})[suffix] = walk[oidleaf]

        # No instanciation if no indexed component found by INDEX or based on NAME
        indexes = []
        if 'INDEX' in walks:
            # Trust INDEX table when present
            indexes = list(walks['INDEX'].values())
        else:
            # Found the most populated info and use related suffixes as index table
            counts = {k: len(v) for k, v in walks.items()}
            larger = max(counts, key=counts.get)
            indexes = list(walks[larger].keys())
        if not indexes:
            return None

        indexes = sorted(indexes, key=int)

        # Checking MAC & IP are for now only supported for Cisco based devices
        mac_indexes_oid = '.1.3.6.1.4.1.9.9.513.1.1.1.1.4'
        mac_indexes = device.walk(mac_indexes_oid)
        if mac_indexes:
            # Get MAC addresses
            macaddresses_oid = '.1.3.6.1.4.1.9.9.513.1.1.1.1.2'
            macaddresses = device.walk(macaddresses_oid) or {}
            # Get IP addresses
            ipaddresses_oid = '.1.3.6.1.4.1.14179.2.2.1.1.19'
            ipaddresses = device.walk(ipaddresses_oid) or {}

            # Populate MAC & IP addresses
            for suffix, index in mac_indexes.items():
                if suffix in macaddresses:
                    walks.setdefault('MAC', {})[index] = macaddresses[suffix]
                if suffix in ipaddresses:
                    walks.setdefault('IP', {})[index] = ipaddresses[suffix]

        # Initialize _components array
        for index in indexes:
            self._components.append({
                'INDEX': getCanonicalConstant(walks.get('INDEX', {}).get(index, index))
            })

        # Dell chassis serialnumbers should be retrieved from a private oid
        dell_serial_numbers = device.walk(PRODUCT_IDENTIFICATION_SERIAL_NUMBER)
        self._dellSN = dell_serial_numbers if dell_serial_numbers and len(dell_serial_numbers) > 1 else None

        self._indexes = indexes
        self._walks = walks

        return self

    def get_physical_components(self):
        # INDEX was still computed during object creation
        keys = sorted([k for k in PHYSICAL_COMPONENTS_VARIABLES if k != 'INDEX'])

        count = len(self._indexes)
        module = 0

        # Populate all components
        for i in range(count):
            component = self._components[i]
            index = self._indexes[i]

            for key in keys:
                variable = PHYSICAL_COMPONENTS_VARIABLES[key]
                type_ = variable.get('type', '')
                raw_value = self._walks.get(key, {}).get(index)
                if raw_value is None:
                    continue
                if type_ == 'type':
                    value = variable['types'].get(raw_value)
                elif type_ == 'mac':
                    value = getCanonicalMacAddress(raw_value)
                elif type_ == 'constant':
                    value = getCanonicalConstant(raw_value)
                elif type_ == 'string':
                    value = getCanonicalString(trimWhitespace(raw_value))
                elif type_ == 'count':
                    value = getCanonicalCount(raw_value)
                else:
                    value = raw_value
                if value is not None and len(str(value)) > 0:
                    component[key] = value

            # Fix Chassis S/N for Dell devices
            if self._dellSN and component.get('TYPE') == 'chassis':
                if component.get('NAME') and re.match(r'^Unit (\d+)$', component['NAME']):
                    module = int(re.match(r'^Unit (\d+)$', component['NAME']).group(1))
                else:
                    module += 1
                serial = getCanonicalSerialNumber(self._dellSN.get(module))
                if serial and (component.get('SERIAL') is None or component['SERIAL'] != serial):
                    component['SERIAL'] = serial

        return self._components
