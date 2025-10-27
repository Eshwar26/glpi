import re

# Mock or simple implementations for GLPI Agent functions/tools
def get_canonical_constant(value):
    # Mock: return int value as string
    try:
        return str(int(value))
    except ValueError:
        return str(value)

def trim_whitespace(value):
    if value is None:
        return None
    return str(value).strip()

def get_canonical_string(value):
    if value is None:
        return None
    return trim_whitespace(value)

def get_canonical_mac_address(value):
    # Mock, not used here
    return value

def get_canonical_count(value):
    # Mock: return count as string
    try:
        return str(int(value))
    except ValueError:
        return str(value)

def get_regexp_oid_match(oid):
    return re.compile(f'^{re.escape(oid)}')

# Simple mock base class for compatibility
class MibSupportTemplate:
    def __init__(self):
        self.device = None  # To be set externally; for testing, can be mocked

    def walk(self, oid):
        # Mock SNMP walk; returns dict of full_oid_suffix: value
        mock_walks = {
            '.1.3.6.1.4.1.6027.3.10.1.2.2.1': {  # chStackUnitEntry walk mock
                '2.1': '1',  # INDEX suffix 2, index 1
                '7.1': 'S4810',  # MODEL suffix 7
                '9.1': 'Force10 S4810',  # DESCRIPTION suffix 9
                '10.1': '5.6.1.0',  # FIRMWARE suffix 10
                '12.1': 'SN123456',  # SERIAL suffix 12
                '21.1': 'A01',  # REVISION suffix 21
                '2.2': '2',  # INDEX for unit 2
                '7.2': 'S4820',  # MODEL for unit 2
            },
            '.1.3.6.1.4.1.6027.3.10.1.2.5.1.5': {  # chSysPortIfIndex
                '1.1': '1',  # suffix for port on unit 1
                '1.2': '2',  # another port
            }
        }
        # Simulate full OID suffixes
        base = oid.replace('.1.3.6.1.4.1.6027.3.10', '')  # Adjust for mock
        return mock_walks.get(oid, {})

# Constants
FORCE10S = '.1.3.6.1.4.1.6027.1.3'

CH_STACK_UNIT_ENTRY = '.1.3.6.1.4.1.6027.3.10.1.2.2.1'

CH_SYS_PORT_IF_INDEX = '.1.3.6.1.4.1.6027.3.10.1.2.5.1.5'

physical_components_variables = {
    'INDEX': {
        'suffix': '2',
        'type': 'integer'
    },
    'MODEL': {
        'suffix': '7',
        'type': 'string'
    },
    'DESCRIPTION': {
        'suffix': '9',
        'type': 'string'
    },
    'FIRMWARE': {
        'suffix': '10',
        'type': 'string'
    },
    'SERIAL': {
        'suffix': '12',
        'type': 'string'
    },
    'REVISION': {
        'suffix': '21',
        'type': 'string'
    },
}

mib_support = [
    {
        'name': "Force10 S-series",
        'sysobjectid': get_regexp_oid_match(FORCE10S)
    }
]

class Force10S(MibSupportTemplate):
    def get_components(self):
        components = []

        stack_components = self._get_stack_units()
        if stack_components:
            components.extend(stack_components)

        ports_components = self._get_ports()
        if ports_components:
            components.extend(ports_components)

        # adding root unit
        if components:
            components.append({
                'CONTAINEDININDEX': '0',
                'INDEX': '-1',
                'TYPE': 'stack',
                'NAME': 'Force10 S-series Stack'
            })

        return components

    def _get_ports(self):
        walk = self.walk(CH_SYS_PORT_IF_INDEX)
        if not walk:
            return None

        ports = []
        for suffix, if_index in walk.items():
            stack_id = _get_element(suffix, -2)
            if stack_id is not None:
                ports.append({
                    'INDEX': if_index,
                    'CONTAINEDININDEX': stack_id,
                    'TYPE': 'port'
                })

        return ports if ports else None

    def _get_stack_units(self):
        walk = self.walk(CH_STACK_UNIT_ENTRY)
        if not walk:
            return None

        # Parse suffixes to only keep what we really need from the walk
        supported = {}
        for key in physical_components_variables:
            suffix = physical_components_variables[key].get('suffix')
            if suffix:
                supported[suffix] = key

        supported_suffixes = sorted(supported.keys(), key=int)
        supported_re = re.compile(f'^({'|'.join(supported_suffixes)})\.(.*)$')
        walks = {}
        for oid_leaf in walk:
            match = supported_re.match(oid_leaf)
            if match:
                node, suffix = match.groups()
                key = supported[node]
                if key not in walks:
                    walks[key] = {}
                walks[key][suffix] = walk[oid_leaf]

        index_walk = walks.get('INDEX', {})
        indexes = list(index_walk.values())
        if not indexes:
            return None

        indexes = sorted(int(i) for i in indexes)

        # Initialize components array
        components = []
        for idx in indexes:
            index_str = get_canonical_constant(index_walk.get(str(idx), str(idx)))
            components.append({
                'INDEX': index_str,
                # minimal chassis number in an interface name is zero, e.g. Gi0/1
                'NAME': str(int(index_str) - 1),
                'CONTAINEDININDEX': '-1',
                'TYPE': 'chassis',
            })

        keys = sorted(k for k in physical_components_variables if k != 'INDEX')

        # Populate all components
        i = 0
        while i < len(indexes):
            component = components[i]
            index = indexes[i]

            for key in keys:
                variable = physical_components_variables[key]
                type_val = variable.get('type', '')
                raw_value = walks.get(key, {}).get(str(index))
                if raw_value is None:
                    continue

                if type_val == 'type':
                    value = variable.get('types', {}).get(raw_value)
                elif type_val == 'mac':
                    value = get_canonical_mac_address(raw_value)
                elif type_val == 'constant':
                    value = get_canonical_constant(raw_value)
                elif type_val == 'string':
                    value = get_canonical_string(trim_whitespace(raw_value))
                elif type_val == 'count':
                    value = get_canonical_count(raw_value)
                else:
                    value = raw_value

                if value is not None and len(str(value)) > 0:
                    component[key] = value

            i += 1

        return components

def _get_element(oid, index_pos):
    array = oid.split('.')
    return array[index_pos] if 0 <= index_pos < len(array) else None

# For testing/standalone run (optional)
if __name__ == "__main__":
    # Test instantiation
    force10s = Force10S()
    components = force10s.get_components()
    print("Components:", components)
    print("Module loaded and run successfully without errors.")
    
