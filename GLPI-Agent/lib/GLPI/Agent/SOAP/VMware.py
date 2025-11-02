"""
GLPI Agent SOAP VMware module

This module allows access to VMware hypervisor using VMware SOAP API
without requiring their Perl library.
"""

import re
from urllib.parse import urlparse
import requests
from requests.cookies import RequestsCookieJar

# Assuming the following are imported or defined elsewhere:
# from glpi.agent import AGENT_STRING
# from glpi.agent.xml import XML
# from glpi.agent.soap.vmware.host import Host

class VMware:
    """
    Equivalent to GLPI::Agent::SOAP::VMware
    Access to VMware hypervisor via SOAP API.
    """
    
    def __init__(self, url=None, timeout=None, **params):
        """
        Initialize a VMware SOAP client.
        
        Args:
            url: The VMware service URL
            timeout: Request timeout in seconds (default: 180)
            **params: Additional parameters
        """
        self.url = url or params.get('url')
        self._last_error = None
        self.vcenter = None
        self.session_manager = None
        self.property_collector = None
        
        # Initialize XML parser
        # Assuming XML class exists with similar interface
        self._xml = XML(
            force_array=['returnval', 'propSet'],
            skip_attr=True  # Skip attributes while dumping as hash
        )
        
        # Create requests session (equivalent to LWP::UserAgent)
        self.session = requests.Session()
        self.session.cookies = RequestsCookieJar()
        
        # Set headers
        self.session.headers.update({
            'User-Agent': AGENT_STRING,
        })
        
        # Set timeout
        self._timeout = timeout or params.get('timeout', 180)
        
        # Disable SSL verification (equivalent to ssl_opts)
        self.session.verify = False
        
        # Suppress SSL warnings
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    def timeout(self, timeout=None):
        """
        Get or set the request timeout.
        
        Args:
            timeout: Optional timeout value to set
            
        Returns:
            int: Current timeout value
        """
        if timeout is not None:
            self._timeout = timeout
        return self._timeout
    
    def lastError(self):
        """
        Get the last error message.
        
        Returns:
            str: The last error message, or empty string if none
        """
        return self._last_error or ''
    
    def _send(self, action, xml_to_send):
        """
        Send a SOAP request to the VMware service.
        
        Args:
            action: The SOAP action name
            xml_to_send: The XML SOAP envelope to send
            
        Returns:
            str or None: Response content on success, None on failure
        """
        headers = {
            'SOAPAction': f'"urn:vim25#{action}"',
            'Accept': 'text/xml, application/soap',
            'Content-Type': 'text/xml; charset=utf-8',
            'Content-Length': str(len(xml_to_send)),
        }
        
        try:
            response = self.session.post(
                self.url,
                data=xml_to_send,
                headers=headers,
                timeout=self._timeout
            )
            
            if response.status_code == 200:
                return response.text
            else:
                # Try to extract fault string from error
                err = response.text
                tmp_ref = None
                
                match = re.search(r'(<faultstring>.*?</faultstring>)', err, re.DOTALL)
                if match:
                    tmp_ref = self._xml.string(match.group(1)).dump_as_hash()
                
                error_string = f"{response.status_code} {response.reason}"
                if tmp_ref and tmp_ref.get('faultstring'):
                    error_string += f": {tmp_ref['faultstring']}"
                
                self._last_error = error_string
                return None
                
        except Exception as e:
            self._last_error = str(e)
            return None
    
    def _parseAnswer(self, answer):
        """
        Parse a SOAP response and extract the return values.
        
        Args:
            answer: The SOAP response string
            
        Returns:
            list or None: Parsed return values, or None on error
        """
        if not answer:
            return None
        
        dump = self._xml.string(answer).dump_as_hash()
        if not dump:
            return None
        
        if 'soapenv:Envelope' not in dump:
            return None
        
        if 'soapenv:Body' not in dump['soapenv:Envelope']:
            return None
        
        body = dump['soapenv:Envelope']['soapenv:Body']
        
        # Get the first key in body (the response element)
        body_keys = list(body.keys())
        if not body_keys:
            return None
        
        body_key = body_keys[0]
        
        if not isinstance(body[body_key], dict) or 'returnval' not in body[body_key]:
            return None
        
        returnval = body[body_key]['returnval']
        
        if not isinstance(returnval, list):
            return None
        
        ref = []
        for val in returnval:
            if isinstance(val.get('propSet'), list):
                tmp = {}
                for p in val['propSet']:
                    if p.get('name') and 'val' in p:
                        tmp[p['name']] = p['val']
                ref.append(tmp)
            else:
                ref.append(val)
        
        return ref
    
    def connect(self, user, password):
        """
        Connect to the VMware service with credentials.
        
        Args:
            user: Username for authentication
            password: Password for authentication
            
        Returns:
            list or None: Parsed response on success, None on failure
        """
        if not user:
            self._last_error = f"No user{'' if self._last_error else ' and password'} provided for ESX connection"
            return None
        
        if not password:
            self._last_error = "No password provided for ESX connection"
            return None
        
        # Retrieve service content
        req = '''<?xml version="1.0" encoding="UTF-8"?>
   <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                     xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
   <soapenv:Body>
<RetrieveServiceContent xmlns="urn:vim25"><_this type="ServiceInstance">ServiceInstance</_this>
</RetrieveServiceContent></soapenv:Body></soapenv:Envelope>'''
        
        answer = self._send('ServiceInstance', req)
        if not answer:
            return None
        
        service_instance = self._parseAnswer(answer)
        if not service_instance:
            return None
        
        # Determine if this is vCenter or ESX
        if service_instance[0].get('about', {}).get('apiType') == 'VirtualCenter':
            self.vcenter = True
            self.session_manager = "SessionManager"
            self.property_collector = "propertyCollector"
        else:
            self.vcenter = False
            self.session_manager = "ha-sessionmgr"
            self.property_collector = "ha-property-collector"
        
        # Login
        login_req = '''<?xml version="1.0" encoding="UTF-8"?>
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
        xmlns:xsd="http://www.w3.org/2001/XMLSchema"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
        <soapenv:Body>
        <Login xmlns="urn:vim25"><_this type="SessionManager">%s</_this>
        <userName>%s</userName><password>%s</password></Login></soapenv:Body></soapenv:Envelope>'''
        
        answer = self._send(
            'Login',
            login_req % (self.session_manager, user, password)
        )
        
        if not answer:
            return None
        
        if re.search(r'ServerFaultCode', answer, re.MULTILINE):
            return None
        
        return self._parseAnswer(answer)
    
    def _getVirtualMachineList(self):
        """
        Get the list of all virtual machine IDs.
        
        Returns:
            list: List of VM IDs
        """
        req = '''<?xml version="1.0" encoding="UTF-8"?>
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
        xmlns:xsd="http://www.w3.org/2001/XMLSchema"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
        <soapenv:Body>
        <RetrieveProperties xmlns="urn:vim25"><_this type="PropertyCollector">ha-property-collector</_this>
        <specSet><propSet><type>VirtualMachine</type><all>0</all></propSet><objectSet><obj type="Folder">ha-folder-root</obj>
        <skip>0</skip><selectSet xsi:type="TraversalSpec"><name>folderTraversalSpec</name><type>Folder</type><path>childEntity</path><skip>0</skip><selectSet><name>folderTraversalSpec</name></selectSet><selectSet><name>datacenterHostTraversalSpec</name></selectSet><selectSet><name>datacenterVmTraversalSpec</name></selectSet><selectSet><name>datacenterDatastoreTraversalSpec</name></selectSet><selectSet><name>datacenterNetworkTraversalSpec</name></selectSet><selectSet><name>computeResourceRpTraversalSpec</name></selectSet><selectSet><name>computeResourceHostTraversalSpec</name></selectSet><selectSet><name>hostVmTraversalSpec</name></selectSet><selectSet><name>resourcePoolVmTraversalSpec</name></selectSet></selectSet><selectSet xsi:type="TraversalSpec"><name>datacenterDatastoreTraversalSpec</name><type>Datacenter</type><path>datastoreFolder</path><skip>0</skip><selectSet><name>folderTraversalSpec</name></selectSet></selectSet><selectSet xsi:type="TraversalSpec"><name>datacenterNetworkTraversalSpec</name><type>Datacenter</type><path>networkFolder</path><skip>0</skip><selectSet><name>folderTraversalSpec</name></selectSet></selectSet><selectSet xsi:type="TraversalSpec"><name>datacenterVmTraversalSpec</name><type>Datacenter</type><path>vmFolder</path><skip>0</skip><selectSet><name>folderTraversalSpec</name></selectSet></selectSet><selectSet xsi:type="TraversalSpec"><name>datacenterHostTraversalSpec</name><type>Datacenter</type><path>hostFolder</path><skip>0</skip><selectSet><name>folderTraversalSpec</name></selectSet></selectSet><selectSet xsi:type="TraversalSpec"><name>computeResourceHostTraversalSpec</name><type>ComputeResource</type><path>host</path><skip>0</skip></selectSet><selectSet xsi:type="TraversalSpec"><name>computeResourceRpTraversalSpec</name><type>ComputeResource</type><path>resourcePool</path><skip>0</skip><selectSet><name>resourcePoolTraversalSpec</name></selectSet><selectSet><name>resourcePoolVmTraversalSpec</name></selectSet></selectSet><selectSet xsi:type="TraversalSpec"><name>resourcePoolTraversalSpec</name><type>ResourcePool</type><path>resourcePool</path><skip>0</skip><selectSet><name>resourcePoolTraversalSpec</name></selectSet><selectSet><name>resourcePoolVmTraversalSpec</name></selectSet></selectSet><selectSet xsi:type="TraversalSpec"><name>hostVmTraversalSpec</name><type>HostSystem</type><path>vm</path><skip>0</skip><selectSet><name>folderTraversalSpec</name></selectSet></selectSet><selectSet xsi:type="TraversalSpec"><name>resourcePoolVmTraversalSpec</name><type>ResourcePool</type><path>vm</path><skip>0</skip></selectSet></objectSet></specSet></RetrieveProperties></soapenv:Body></soapenv:Envelope>'''
        
        answer = self._send('RetrievePropertiesVMList', req)
        ref = self._parseAnswer(answer)
        
        vm_list = []
        if isinstance(ref, dict):
            vm_list = [ref]
        elif isinstance(ref, list):
            vm_list = ref
        
        ids = []
        for item in vm_list:
            if 'obj' in item:
                ids.append(item['obj'])
        
        return ids
    
    def _getVirtualMachineById(self, vm_id):
        """
        Get detailed information about a specific virtual machine.
        
        Args:
            vm_id: The virtual machine ID
            
        Returns:
            list: VM information
        """
        req = '''<?xml version="1.0" encoding="UTF-8"?>
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
        xmlns:xsd="http://www.w3.org/2001/XMLSchema"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
        <soapenv:Body>
        <RetrieveProperties xmlns="urn:vim25"><_this type="PropertyCollector">%s</_this>
        <specSet><propSet><type>VirtualMachine</type><all>1</all></propSet><objectSet><obj type="VirtualMachine">%s</obj>
        </objectSet></specSet></RetrieveProperties></soapenv:Body></soapenv:Envelope>'''
        
        answer = self._send(
            'RetrieveProperties',
            req % (self.property_collector, vm_id)
        )
        
        if not answer:
            return []
        
        return self._parseAnswer(answer) or []
    
    def getHostFullInfo(self, host_id=None):
        """
        Get full information about a host including all VMs.
        
        Args:
            host_id: The host ID (default: 'ha-host')
            
        Returns:
            Host: Host object with full information
        """
        if not host_id:
            host_id = 'ha-host'
        
        req = '''<?xml version="1.0" encoding="UTF-8"?>
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
        xmlns:xsd="http://www.w3.org/2001/XMLSchema"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
        <soapenv:Body>
        <RetrieveProperties xmlns="urn:vim25"><_this type="PropertyCollector">%s</_this>
        <specSet><propSet><type>HostSystem</type><all>1</all></propSet><objectSet><obj type="HostSystem">%s</obj>
        </objectSet></specSet></RetrieveProperties></soapenv:Body></soapenv:Envelope>'''
        
        answer = self._send(
            'RetrieveProperties',
            req % (self.property_collector, host_id)
        )
        
        ref = self._parseAnswer(answer) or []
        vms = []
        machine_id_list = []
        
        # Extract VM list from host info
        vm = ""
        if isinstance(ref, list) and ref and isinstance(ref[0], dict) and 'vm' in ref[0]:
            vm = ref[0]['vm']
        
        # vm can be an empty string for vCenter 7
        if isinstance(vm, dict) and 'ManagedObjectReference' in vm:  # ESX 3.5
            if isinstance(vm['ManagedObjectReference'], list):
                machine_id_list = vm['ManagedObjectReference']
            else:
                machine_id_list = [vm['ManagedObjectReference']]
        else:
            machine_id_list = self._getVirtualMachineList()
        
        # Get details for each VM
        for vm_id in machine_id_list:
            vms.append(self._getVirtualMachineById(vm_id))
        
        # Create Host object
        host = Host(hash=ref, vms=vms)
        return host
    
    def getHostIds(self):
        """
        Get the list of all host IDs.
        
        Returns:
            list: List of host IDs
        """
        if not self.vcenter:
            return ['ha-host']
        
        req = '''<?xml version="1.0" encoding="UTF-8"?>
   <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                     xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
   <soapenv:Body>
<RetrieveProperties xmlns="urn:vim25"><_this type="PropertyCollector">propertyCollector</_this>
<specSet><propSet><type>HostSystem</type><all>0</all></propSet><objectSet><obj type="Folder">group-d1</obj>
<skip>0</skip><selectSet xsi:type="TraversalSpec"><name>folderTraversalSpec</name><type>Folder</type><path>childEntity</path><skip>0</skip><selectSet><name>folderTraversalSpec</name></selectSet><selectSet><name>datacenterHostTraversalSpec</name></selectSet><selectSet><name>datacenterVmTraversalSpec</name></selectSet><selectSet><name>datacenterDatastoreTraversalSpec</name></selectSet><selectSet><name>datacenterNetworkTraversalSpec</name></selectSet><selectSet><name>computeResourceRpTraversalSpec</name></selectSet><selectSet><name>computeResourceHostTraversalSpec</name></selectSet><selectSet><name>hostVmTraversalSpec</name></selectSet><selectSet><name>resourcePoolVmTraversalSpec</name></selectSet></selectSet><selectSet xsi:type="TraversalSpec"><name>datacenterDatastoreTraversalSpec</name><type>Datacenter</type><path>datastoreFolder</path><skip>0</skip><selectSet><name>folderTraversalSpec</name></selectSet></selectSet><selectSet xsi:type="TraversalSpec"><name>datacenterNetworkTraversalSpec</name><type>Datacenter</type><path>networkFolder</path><skip>0</skip><selectSet><name>folderTraversalSpec</name></selectSet></selectSet><selectSet xsi:type="TraversalSpec"><name>datacenterVmTraversalSpec</name><type>Datacenter</type><path>vmFolder</path><skip>0</skip><selectSet><name>folderTraversalSpec</name></selectSet></selectSet><selectSet xsi:type="TraversalSpec"><name>datacenterHostTraversalSpec</name><type>Datacenter</type><path>hostFolder</path><skip>0</skip><selectSet><name>folderTraversalSpec</name></selectSet></selectSet><selectSet xsi:type="TraversalSpec"><name>computeResourceHostTraversalSpec</name><type>ComputeResource</type><path>host</path><skip>0</skip></selectSet><selectSet xsi:type="TraversalSpec"><name>computeResourceRpTraversalSpec</name><type>ComputeResource</type><path>resourcePool</path><skip>0</skip><selectSet><name>resourcePoolTraversalSpec</name></selectSet><selectSet><name>resourcePoolVmTraversalSpec</name></selectSet></selectSet><selectSet xsi:type="TraversalSpec"><name>resourcePoolTraversalSpec</name><type>ResourcePool</type><path>resourcePool</path><skip>0</skip><selectSet><name>resourcePoolTraversalSpec</name></selectSet><selectSet><name>resourcePoolVmTraversalSpec</name></selectSet></selectSet><selectSet xsi:type="TraversalSpec"><name>hostVmTraversalSpec</name><type>HostSystem</type><path>vm</path><skip>0</skip><selectSet><name>folderTraversalSpec</name></selectSet></selectSet><selectSet xsi:type="TraversalSpec"><name>resourcePoolVmTraversalSpec</name><type>ResourcePool</type><path>vm</path><skip>0</skip></selectSet></objectSet></specSet></RetrieveProperties></soapenv:Body></soapenv:Envelope>'''
        
        answer = self._send('RetrieveProperties', req)
        ref = self._parseAnswer(answer) or []
        
        ids = []
        for item in ref:
            if 'obj' in item:
                ids.append(item['obj'])
        
        return ids