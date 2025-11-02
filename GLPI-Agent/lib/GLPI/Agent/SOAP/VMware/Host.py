import re
import uuid as uuid_module
from typing import Any, Dict, List, Optional, Union

# Assuming the following are imported or defined elsewhere:
# from glpi.agent.tools import empty, glpi_version
# from glpi.agent.tools.virtualization import STATUS_RUNNING, STATUS_OFF, STATUS_PAUSED
# from glpi.agent.tools import get_canonical_manufacturer  # Assuming this exists

# Define if not available
def empty(value: Any) -> bool:
    return value is None or value == '' or (isinstance(value, (list, dict)) and not value)

def glpi_version(version: str) -> float:
    # Placeholder: map version string to float, e.g., '9.5' -> 9.5, '10.0.17' -> 10.0017
    # Implement based on actual logic
    return float(version.replace('.', '')[:4]) / 100  # Simple placeholder

STATUS_RUNNING = 'running'
STATUS_OFF = 'off'
STATUS_PAUSED = 'paused'


class VMwareHost:
    """
    Equivalent to GLPI::Agent::SOAP::VMware::Host
    VMware Host abstraction layer.
    """

    def __init__(self, **params):
        self.hash_ = params.get('hash', [])  # List of dicts
        self.vms = params.get('vms', [])
        self.glpi = None

    def _as_array(self, h: Any) -> List[Any]:
        if isinstance(h, list):
            return h
        elif h:
            return [h]
        else:
            return []

    def enable_features_for_glpi_version(self, version: str):
        if not empty(version):
            self.glpi = glpi_version(version)

    def support_glpi_version(self, version: str) -> bool:
        return self.glpi is not None and self.glpi >= glpi_version(version)

    def get_boot_time(self) -> Optional[str]:
        return self.hash_[0]['summary']['runtime'].get('bootTime')

    def get_hostname(self) -> Optional[str]:
        return self.hash_[0].get('name')

    def get_bios_info(self) -> Optional[Dict[str, str]]:
        if not self.hash_:
            return None
        hardware = self.hash_[0]['hardware']
        bios_info = hardware.get('biosInfo')
        system_info = hardware.get('systemInfo')
        if not isinstance(bios_info, dict):
            return None

        bios = {
            'BDATE': bios_info.get('releaseDate', ''),
            'BVERSION': bios_info.get('biosVersion', ''),
            'SMODEL': system_info.get('model', '') if isinstance(system_info, dict) else '',
            'SMANUFACTURER': system_info.get('vendor', '') if isinstance(system_info, dict) else '',
        }

        other_identifying_info = system_info.get('otherIdentifyingInfo') if isinstance(system_info, dict) else None
        if isinstance(other_identifying_info, dict):
            bios['ASSETTAG'] = other_identifying_info.get('identifierValue', '')
        elif isinstance(other_identifying_info, list):
            ssn_set = False
            for info in other_identifying_info:
                if not isinstance(info, dict) or 'identifierType' not in info:
                    continue
                key = info['identifierType'].get('key', '')
                value = info.get('identifierValue', '')
                if key == 'ServiceTag':
                    if 'SSN' in bios:
                        bios['MSN'] = bios['SSN']
                    bios['SSN'] = value
                    ssn_set = True
                elif key == 'AssetTag':
                    bios['ASSETTAG'] = value
                elif key == 'EnclosureSerialNumberTag':
                    bios['MSN'] = value
                elif key == 'SerialNumberTag':
                    bios['SSN'] = value

        return bios

    def get_hardware_info(self) -> Dict[str, Any]:
        if not self.hash_:
            return {}
        host = self.hash_[0]
        dns_config = host.get('config', {}).get('network', {}).get('dnsConfig', {})
        hardware = host.get('hardware', {})
        summary = host.get('summary', {})
        system_info = hardware.get('systemInfo', {})

        return {
            'NAME': dns_config.get('hostName', ''),
            'DNS': '/'.join(self._as_array(dns_config.get('address', []))),
            'WORKGROUP': dns_config.get('domainName', ''),
            'MEMORY': int(hardware.get('memorySize', 0) / (1024 * 1024)),
            'UUID': summary.get('hardware', {}).get('uuid') or system_info.get('uuid', ''),
        }

    def get_operating_system_info(self) -> Dict[str, Any]:
        if not self.hash_:
            return {}
        host = self.hash_[0]
        dns_config = host.get('config', {}).get('network', {}).get('dnsConfig', {})
        product = host.get('summary', {}).get('config', {}).get('product', {})

        boot_time_raw = host.get('summary', {}).get('runtime', {}).get('bootTime', '')
        bootdate_match = re.match(r'^([0-9-]+)T([0-9:]+)\.', boot_time_raw)
        bootdate, boottime = bootdate_match.groups() if bootdate_match else ('', '')
        boottime = f"{bootdate} {boottime}" if bootdate and boottime else ''

        os_info = {
            'NAME': product.get('name', ''),
            'VERSION': product.get('version', ''),
            'FULL_NAME': product.get('fullName', ''),
            'FQDN': host.get('name', ''),
            'DNS_DOMAIN': dns_config.get('domainName', ''),
            'BOOT_TIME': boottime,
        }

        dtinfo = host.get('config', {}).get('dateTimeInfo', {})
        timezone = dtinfo.get('timeZone', {}) if isinstance(dtinfo, dict) else {}
        offset = timezone.get('gmtOffset')
        if offset is not None:
            offset_hours = offset / 3600
            sign = '-' if offset_hours < 0 else '+'
            abs_offset = abs(offset_hours) * 100
            os_info['TIMEZONE'] = {
                'NAME': timezone.get('name', ''),
                'OFFSET': f"{sign}{abs_offset:04d}",
            }

        return os_info

    def get_cpus(self) -> List[Dict[str, Any]]:
        if not self.hash_:
            return []
        hardware = self.hash_[0]['hardware']
        cpu_info = hardware.get('cpuInfo', {})
        total_cores = cpu_info.get('numCpuCores', 0)
        total_threads = cpu_info.get('numCpuThreads', 0)
        cpu_entries = self._as_array(hardware.get('cpuPkg', []))
        cpu_packages = cpu_info.get('numCpuPackages') or len(cpu_entries)

        cpu_manufacturer_map = {
            'amd': 'AMD',
            'intel': 'Intel',
        }

        cpus = []
        core_per_pkg = total_cores / cpu_packages if cpu_packages else 0
        thread_per_core = total_threads / total_cores if total_cores else 0

        for entry in cpu_entries:
            if not isinstance(entry, dict):
                continue
            cpus.append({
                'CORE': core_per_pkg,
                'MANUFACTURER': cpu_manufacturer_map.get(entry.get('vendor', '').lower(), entry.get('vendor', '')),
                'NAME': entry.get('description', ''),
                'SPEED': int(entry.get('hz', 0) / (1000 * 1000)),
                'THREAD': thread_per_core,
            })

        return cpus

    def get_controllers(self) -> List[Dict[str, str]]:
        if not self.hash_:
            return []
        pci_devices = self._as_array(self.hash_[0].get('hardware', {}).get('pciDevice', []))

        controllers = []
        for device in pci_devices:
            if not isinstance(device, dict):
                continue
            controller = {
                'NAME': device.get('deviceName', ''),
                'MANUFACTURER': device.get('vendorName', ''),
                'PCICLASS': f"{device.get('classId', 0):04x}"[-4:],
                'VENDORID': f"{device.get('vendorId', 0):04x}"[-4:],
                'PRODUCTID': f"{device.get('deviceId', 0):04x}"[-4:],
                'PCISLOT': device.get('id', ''),
            }
            sub_vendor_id = device.get('subVendorId')
            sub_device_id = device.get('subDeviceId')
            if sub_vendor_id is not None or sub_device_id is not None:
                controller['PCISUBSYSTEMID'] = f"{sub_vendor_id:04x}[:]{sub_device_id:04x}"[-9:]  # Mimic Perl concat

            controllers.append(controller)

        return controllers

    def _get_nic(self, ref: Dict[str, Any], is_virtual: bool) -> Dict[str, Any]:
        nic = {
            'VIRTUALDEV': is_virtual,
        }

        binding_map = {
            'DESCRIPTION': 'device',
            'DRIVER': 'driver',
            'PCISLOT': 'pci',
            'MACADDR': 'mac',
        }

        for key, dump_key in binding_map.items():
            if dump_key in ref:
                nic[key] = ref[dump_key]

        spec = ref.get('spec', {})
        if spec:
            ip = spec.get('ip', {})
            if ip:
                nic['IPADDRESS'] = ip.get('ipAddress') if 'ipAddress' in ip else ''
                nic['IPMASK'] = ip.get('subnetMask') if 'subnetMask' in ip else ''
            if 'MACADDR' not in nic and 'mac' in spec:
                nic['MACADDR'] = spec['mac']
            if 'mtu' in spec:
                nic['MTU'] = spec['mtu']
            link_speed = spec.get('linkSpeed', {})
            if 'speedMb' in link_speed:
                nic['SPEED'] = link_speed['speedMb']

        nic['STATUS'] = 'Up' if nic.get('IPADDRESS') else 'Down'

        return nic

    def get_networks(self) -> List[Dict[str, Any]]:
        if not self.hash_:
            return []
        host = self.hash_[0]
        config = host.get('config', {})
        network_config = config.get('network', {})

        seen = {}
        networks = []

        for nic_type in ['vnic', 'pnic', 'consoleVnic']:
            nic_entries = self._as_array(network_config.get(nic_type, []))
            for entry in nic_entries:
                device = entry.get('device', '')
                if device in seen:
                    continue
                seen[device] = True
                is_virtual = nic_type == 'vnic'
                networks.append(self._get_nic(entry, is_virtual))

        vnic_entries = []
        console_vnic = config.get('network', {}).get('consoleVnic')
        if console_vnic:
            vnic_entries.append(console_vnic)
        vmotion_netconfig = config.get('vmotion', {}).get('netConfig', {})
        candidate_vnic = vmotion_netconfig.get('candidateVnic')
        if candidate_vnic:
            vnic_entries.append(candidate_vnic)

        for entry in vnic_entries:
            nic_list = self._as_array(entry)
            for nic_entry in nic_list:
                device = nic_entry.get('device', '')
                if device in seen:
                    continue
                seen[device] = True
                networks.append(self._get_nic(nic_entry, True))

        return networks

    def get_storages(self) -> List[Dict[str, Any]]:
        if not self.hash_:
            return []
        scsi_luns = self._as_array(self.hash_[0].get('config', {}).get('storageDevice', {}).get('scsiLun', []))

        storages = []
        for entry in scsi_luns:
            if not isinstance(entry, dict):
                continue
            serialnumber = ''
            alt_names = self._as_array(entry.get('alternateName', []))
            for alt_name in alt_names:
                if not isinstance(alt_name, dict) or not alt_name.get('namespace') or 'data' not in alt_name:
                    continue
                if alt_name['namespace'] == 'SERIALNUM':
                    serialnumber += ''.join(self._as_array(alt_name['data']))

            capacity = entry.get('capacity', {})
            size = 0
            if 'blockSize' in capacity and 'block' in capacity:
                size = int((capacity['blockSize'] * capacity['block']) / 1024 / 1024)

            vendor = entry.get('vendor', '')
            manufacturer = vendor if vendor and not re.match(r'^\s*ATA\s*$', vendor) else get_canonical_manufacturer(entry.get('model', ''))
            manufacturer = re.sub(r'\s*(\S.*\S)\s*', r'\1', manufacturer)

            model = re.sub(r'\s*(\S.*\S)\s*', r'\1', entry.get('model', ''))

            storages.append({
                'DESCRIPTION': entry.get('displayName', ''),
                'DISKSIZE': size,
                'MANUFACTURER': manufacturer,
                'MODEL': model,
                'NAME': entry.get('deviceName', ''),
                'TYPE': entry.get('deviceType', ''),
                'SERIAL': serialnumber,
                'FIRMWARE': entry.get('revision', ''),
            })

        return storages

    def get_drives(self) -> List[Dict[str, Any]]:
        if not self.hash_:
            return []
        mount_infos = self._as_array(self.hash_[0].get('config', {}).get('fileSystemVolume', {}).get('mountInfo', []))

        drives = []
        for mount_info in mount_infos:
            if not isinstance(mount_info, dict):
                continue
            volume = mount_info.get('volume', {})
            volumn = ''
            volume_type = volume.get('type', '')
            if volume_type and re.search(r'NFS', volume_type, re.I):
                volumn = f"{volume.get('remoteHost', '')}:{volume.get('remotePath', '')}"

            total = int((volume.get('capacity', 0) or 0) / (1000 * 1000))

            drives.append({
                'SERIAL': volume.get('uuid', ''),
                'TOTAL': total,
                'TYPE': mount_info.get('mountInfo', {}).get('path', ''),
                'VOLUMN': volumn,
                'LABEL': volume.get('name', ''),
                'FILESYSTEM': volume_type.lower() if volume_type else '',
            })

        return drives

    def get_virtual_machines(self) -> List[Dict[str, Any]]:
        if not self.vms:
            return []

        virtual_machines = []
        for vm in self.vms:
            if not vm or not isinstance(vm, list) or not vm[0]:
                continue
            machine = vm[0]
            power_state = machine.get('summary', {}).get('runtime', {}).get('powerState', '')
            status = (
                STATUS_RUNNING if power_state == 'poweredOn' else
                STATUS_OFF if power_state == 'poweredOff' else
                STATUS_PAUSED if power_state == 'suspended' else
                None
            )
            if status is None:
                print(f"Unknown status ({power_state})")

            macs = []
            devices = self._as_array(machine.get('config', {}).get('hardware', {}).get('device', []))
            for device in devices:
                if isinstance(device, dict) and 'macAddress' in device:
                    macs.append(device['macAddress'])

            comment = machine.get('config', {}).get('annotation', '')
            if comment:
                comment = re.sub(r'\n', '&#10;', comment, flags=re.M)

            if machine.get('summary', {}).get('config', {}).get('template') == 'true':
                continue

            vm_uuid = machine.get('summary', {}).get('config', {}).get('uuid', '')
            serial = ''
            if is_uuid_string(vm_uuid):
                parts = re.findall(r'[0-9a-fA-F]{2}', vm_uuid)
                if len(parts) == 16:
                    first_part = ' '.join(parts[:8])
                    second_part = ' '.join(parts[8:])
                    serial = f"VMware-{first_part}-{second_part}"

            vm_inventory = {
                'NAME': machine.get('name', ''),
                'STATUS': status,
                'UUID': vm_uuid,
                'MEMORY': machine.get('summary', {}).get('config', {}).get('memorySizeMB', 0),
                'VMTYPE': 'VMware',
                'VCPU': machine.get('summary', {}).get('config', {}).get('numCpu', 0),
                'MAC': '/'.join(macs),
                'COMMENT': comment,
                'SERIAL': serial,
            }

            if self.support_glpi_version('10.0.17'):
                summary_guest = machine.get('summary', {}).get('guest', {})
                if isinstance(summary_guest, dict):
                    ip_address = summary_guest.get('ipAddress')
                    if not empty(ip_address):
                        vm_inventory['IPADDRESS'] = ip_address
                    guest_full_name = summary_guest.get('guestFullName')
                    if not empty(guest_full_name):
                        if 'OPERATINGSYSTEM' not in vm_inventory:
                            vm_inventory['OPERATINGSYSTEM'] = {}
                        vm_inventory['OPERATINGSYSTEM']['FULL_NAME'] = guest_full_name

                guest = machine.get('guest', {})
                if isinstance(guest, dict):
                    host_name = guest.get('hostName')
                    if not empty(host_name):
                        if 'OPERATINGSYSTEM' not in vm_inventory:
                            vm_inventory['OPERATINGSYSTEM'] = {}
                        vm_inventory['OPERATINGSYSTEM']['FQDN'] = host_name

                    guest_net = guest.get('net')
                    if guest_net:
                        guest_nets = self._as_array(guest_net)
                        for gnet in guest_nets:
                            if not isinstance(gnet, dict) or 'dnsConfig' not in gnet:
                                continue
                            dns_config = self._as_array(gnet['dnsConfig'])[0] if isinstance(gnet['dnsConfig'], list) else gnet['dnsConfig']
                            if isinstance(dns_config, dict) and not empty(dns_config.get('domainName')):
                                if 'OPERATINGSYSTEM' not in vm_inventory:
                                    vm_inventory['OPERATINGSYSTEM'] = {}
                                vm_inventory['OPERATINGSYSTEM']['DNS_DOMAIN'] = dns_config['domainName']
                                break

                vm_boot_time = machine.get('summary', {}).get('runtime', {}).get('bootTime', '')
                if not empty(vm_boot_time):
                    boot_match = re.match(r'^([0-9-]+).(\d+:\d+:\d+)', vm_boot_time)
                    if boot_match:
                        bootdate, boottime = boot_match.groups()
                        boottime = f"{bootdate} {boottime}"
                        if 'OPERATINGSYSTEM' not in vm_inventory:
                            vm_inventory['OPERATINGSYSTEM'] = {}
                        vm_inventory['OPERATINGSYSTEM']['BOOT_TIME'] = boottime

            virtual_machines.append(vm_inventory)

        return virtual_machines


def is_uuid_string(uuid_str: str) -> bool:
    try:
        return str(uuid_module.UUID(uuid_str)) == uuid_str
    except ValueError:
        return False


"""
__END__

=head1 NAME

GLPI::Agent::SOAP::VMware::Host - VMware Host abstraction layer

=head1 DESCRIPTION

The module is an abstraction layer to access the VMware host.

=head1 FUNCTIONS

=head2 new($class, %params)

Returns an object.

=head2 getBootTime( $self )

Returns the date in the following format: 2012-12-31T12:59:59

=head2 getHostname( $self )

Returns the host name.

=head2 getBiosInfo( $self )

Returns the BIOS (BDATE, BVERSION, SMODEL, SMANUFACTURER, ASSETTAG, SSN)
information in an HASH reference.

=head2 getHardwareInfo( $self )

Returns hardware information in a hash reference.

=head2 getCPUs( $self )

Returns CPU information (hash ref) in an array.

=head2 getControllers( $self )

Returns PCI controller information (hash ref) in an
array.

=head2 getNetworks( $self )

Returns the networks configuration in an array.


=head2 getStorages( $self )

Returns the storage devices in an array.

=head2 getDrives( $self )

Returns the hard drive partitions in an array.

=head2 getVirtualMachines( $self )

Retuns the Virtual Machines in an array.
"""