import os
import re
import uuid
from typing import Dict, Any, List, Optional

# --- MOCK CLASSES AND GLOBAL UTILITIES ---
# These classes mock the behavior of the required Perl modules and custom WS-Man classes.
# Their methods are designed to be minimally sufficient to allow WsManClient's logic to execute.

class HTTPClient:
    """
    Mock base class for GLPI::Agent::HTTP::Client.
    Provides basic HTTP client functionality and logging/error tracking.
    """
    def __init__(self, **kwargs):
        self._lasterror = ""
        self.logger = kwargs.get('logger')
        self._url = kwargs.get('url')

    def request(self, request: 'HTTP_Request', **kwargs) -> 'HTTP_Response':
        """
        Mocks sending an HTTP request. The real implementation would use
        a library like 'requests'. This mock returns a generic successful response.
        The Perl code specifically handles error 500 via the '500 => 1' option,
        which is generally passed to a lower-level HTTP client library.
        """
        # In a real scenario, this would execute the network request.
        class HTTP_Response:
            def __init__(self, status_code, content=None, headers=None, status_line=""):
                self.status_code = status_code
                self._content = content if content is not None else ""
                self._headers = headers if headers is not None else {}
                self._status_line = status_line

            def is_success(self) -> bool:
                return 200 <= self.status_code < 300

            def content(self) -> str:
                return self._content

            def header(self, name: str) -> Optional[str]:
                return self._headers.get(name)

            def as_string(self) -> str:
                return f"Status: {self.status_code}\nContent:\n{self._content}"

            def status_line(self) -> str:
                return self._status_line or f"{self.status_code} Status Line Mock"

        # Mock successful response
        return HTTP_Response(
            status_code=200,
            content="<s:Envelope><s:Header/><s:Body/></s:Envelope>",
            status_line="200 OK"
        )

    def url(self) -> Optional[str]:
        """Returns the base URL."""
        return self._url

    def lasterror(self, error: Optional[str] = None) -> str:
        """Sets or gets the last error."""
        if error is not None:
            self._lasterror = error
        return self._lasterror

    def debug(self, message: Optional[str] = None) -> Any:
        """Mocks debug logging."""
        if self.logger:
            if message is None:
                return self.logger.debug_level()
            self.logger.debug(message)
        return False

    def debug2(self, message: str):
        """Mocks verbose debug logging."""
        if self.logger:
            self.logger.debug2(message)

# Mock HTTP Request/Headers
class HTTP_Request:
    def __init__(self, method, url, headers, message):
        self.method = method
        self.url = url
        self.headers = headers
        self.message = message

    def as_string(self) -> str:
        return f"Method: {self.method}\nURL: {self.url}\nHeaders: {self.headers}\nMessage:\n{self.message}"

class HTTP_Headers:
    def __init__(self, **kwargs):
        self.headers = kwargs

    def new(self, **kwargs):
        return self.headers.update(kwargs)

    def __getitem__(self, key):
        return self.headers.get(key)

# Mock XML Utility Class
class GLPIAgentXML:
    """Mock for GLPI::Agent::XML module."""
    def __init__(self, **kwargs):
        self._xml_format = kwargs.get('xml_format', 0)
        self._string = ""
        self._hash = {}

    def write(self, structure: Dict[str, Any]) -> Optional[str]:
        """Mocks converting a structure (likely a dict) into an XML string."""
        # In a real scenario, this would use a library like lxml or defusedxml.
        if structure:
            return f"<xml>{structure}</xml>"
        return None

    def string(self, xml_string: str):
        """Sets the XML string to be parsed."""
        self._string = xml_string

    def dump_as_hash(self) -> Dict[str, Any]:
        """Mocks parsing the XML string back into a nested hash/dict structure."""
        # This is a very complex operation in reality. Mocking a simple dict return.
        return self._hash or {"s:Envelope": {"s:Header": {}, "s:Body": {}}}

    def dump_as_hash_for_test(self, mock_hash):
        self._hash = mock_hash

    def reset(self):
        self._string = ""
        self._hash = {}

# Mock WS-Man Element Classes (Used for composition)
class WsManElement:
    """Base class for all WS-Man SOAP elements."""
    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs
        self._content = {}

    def get(self, key: Optional[str] = None) -> Any:
        return self._content.get(key) if key else self._content

    def string(self) -> str:
        return str(self._args[0]) if self._args else ""

    def is(self, value: str) -> bool:
        return self.string().lower() == value.lower()

    def isvalid(self) -> bool:
        return True # Mock always valid

    def reset_namespace(self, namespaces: Optional[str] = None):
        pass # Mock implementation

    def nodes(self) -> List['WsManElement']:
        return []

class Node(WsManElement): pass
class Attribute(WsManElement): pass
class Namespace(WsManElement): pass
class Identify(WsManElement): pass
class ResourceURI(WsManElement): pass
class To(WsManElement): pass
class ReplyTo(WsManElement):
    def anonymous(self): return self # Mock a static method
class MaxEnvelopeSize(WsManElement): pass
class Locale(WsManElement): pass
class DataLocale(WsManElement): pass
class SessionId(WsManElement):
    def reset_uuid(self): self._uuid = str(uuid.uuid4())
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reset_uuid()
class OperationID(SessionId): pass
class MessageID(SessionId): pass
class SequenceId(WsManElement): pass
class OperationTimeout(WsManElement): pass
class Enumerate(WsManElement): pass
class Pull(WsManElement): pass
class Option(WsManElement): pass
class OptionSet(WsManElement): pass
class Shell(WsManElement):
    def commandline(self, command: str) -> 'WsManElement':
        return WsManElement(command)
    @staticmethod
    def xmlns(): return "http://schemas.microsoft.com/wbem/wsman/1/windows/shell"
    @staticmethod
    def xsd(): return "http://schemas.microsoft.com/wbem/wsman/1/windows/shell"
class Signal(WsManElement): pass
class Receive(WsManElement): pass
class Code(WsManElement):
    @staticmethod
    def signal(signal: str) -> 'Code': return Code(signal)
class Filter(WsManElement): pass
class OptimizeEnumeration(WsManElement): pass
class MaxElements(WsManElement): pass
class SelectorSet(WsManElement): pass
class Selector(WsManElement): pass
class CommandId(WsManElement): pass

class Action(WsManElement):
    def set(self, action: str):
        self._args = (action,)
    def what(self) -> str:
        return self.string()

class Header(WsManElement):
    def action(self) -> Action:
        return self.get('Action') or Action()
    def get(self, key: str) -> Optional[WsManElement]:
        return self._content.get(key)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._content = {type(a).__name__: a for a in args if isinstance(a, WsManElement)}

class Body(WsManElement):
    def reset(self, new_element: WsManElement):
        self._content = new_element.get()
    def enumeration(self, is_pull: bool) -> 'Enumeration':
        return Enumeration()
    @property
    def fault(self) -> 'WsManElement': return WsManElement()

class Envelope(WsManElement):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._header = next((a for a in args if isinstance(a, Header)), Header())
        self._body = next((a for a in args if isinstance(a, Body)), Body())
        # Mocking the hash-based construction from _send response
        if args and isinstance(args[0], dict):
            self._hash_data = args[0]
            # Simple mock of content extraction
            self._header = Header({'Action': Action(self._hash_data.get('Action', ''))})
            self._body = Body({'IdentifyResponse': Identify()})

    @property
    def header(self) -> Header: return self._header
    @property
    def body(self) -> Body: return self._body
    def get(self) -> Dict[str, Any]:
        return {"Header": self.header.get(), "Body": self.body.get()}
    def reset_namespace(self, namespaces: str): pass
    def attribute(self, name: str) -> Optional[str]: return None # Mock language extraction

class Enumeration(WsManElement):
    """Mock for the enumeration result object."""
    def items(self) -> List[Dict[str, Any]]:
        # Mock returns a list of resource items (dicts)
        return [{"CreationClassName": "Win32_Thing", "SelectorProp": "Value1"}]
    def end_of_sequence(self) -> bool: return True
    @property
    def context(self) -> str: return "MockContext"

# Global Variables (Module level state, mirroring Perl)
_xml: Optional[GLPIAgentXML] = None
_wsman_debug: bool = os.environ.get('WSMAN_DEBUG') is not None
_HIVEREF: Dict[str, int] = {
    'HKEY_CLASSES_ROOT': 0x80000000,
    'HKEY_CURRENT_USER': 0x80000001,
    'HKEY_LOCAL_MACHINE': 0x80000002,
    'HKEY_USERS': 0x80000003,
    'HKEY_CURRENT_CONFIG': 0x80000005
}

# --- HELPER FUNCTIONS ---

def _extract(item: Any, properties: Optional[List[str]] = None) -> Any:
    """
    Recursively extracts specified properties from a nested hash structure,
    mirroring the Perl logic to deep-copy selected keys.
    """
    if not isinstance(item, dict) or not isinstance(properties, list):
        return item

    result: Dict[str, Any] = {}

    for prop in properties:
        value = item.get(prop)
        if isinstance(value, list):
            # Copy array items
            result[prop] = [v for v in value]
        elif isinstance(value, dict):
            # Recurse for nested hashes, using all keys as properties to extract
            result[prop] = _extract(value, list(value.keys()))
        else:
            # Copy scalar value
            result[prop] = value

    return result

# --- MAIN WS-MAN CLIENT CLASS ---

class WsManClient(HTTPClient):
    """
    Python equivalent of GLPI::Agent::SOAP::WsMan, implementing
    WS-Man protocol operations over HTTP.
    """

    def __init__(self, **params: Any):
        """Initializes the WS-Man client."""
        global _xml

        config: Dict[str, Any] = params.get('config', {})

        # 1. Parent initialization (Perl's SUPER::new)
        super().__init__(
            ca_cert_dir=config.get('ca_cert_dir') or os.environ.get('CA_CERT_PATH'),
            ca_cert_file=config.get('ca_cert_file') or os.environ.get('CA_CERT_FILE'),
            ssl_cert_file=config.get('ssl_cert_file') or os.environ.get('SSL_CERT_FILE'),
            **params
        )

        # 2. Instance attributes
        self._url = params.get('url')
        self._lang = 'en-US'
        self._winrm = params.get('winrm', 0)
        self._noauth = 0 if params.get('user') and params.get('password') else 1
        self._lastresponse = None
        self._resource_class = None
        self._exitcode = None

        # 3. Global XML utility setup (Perl's singleton check)
        if _xml is None:
            # Note: 'first_out' is Perl-specific XML-builder instruction. Mocked here.
            _xml = GLPIAgentXML(
                first_out=['s:Header'],
                no_xml_decl='',
                xml_format=0,
            )

    def abort(self, message: str) -> None:
        """Sets the last error and logs a debug message."""
        self.lasterror(message)
        self.debug2(message)
        return

    def _send(self, envelope: Envelope, header: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Builds the SOAP message, sends the HTTP request, and parses the response.
        """
        global _xml, _wsman_debug

        header = header or {}
        message = _xml.write(envelope.get())

        if not message:
            return self.abort("Won't send wrong request")

        headers = {
            'Content-Type': 'application/soap+xml;charset=UTF-8',
            'Content-length': str(len(message)),
            **header,
        }

        # The Perl code uses HTTP::Request/Headers objects, adapting to use mocks
        # compatible with the base class's request method.
        request = HTTP_Request('POST', self.url(), HTTP_Headers(**headers), message)

        if _wsman_debug:
            print("===>\n", request.as_string(), "===>\n", file=sys.stderr)

        # Get response ignoring logging of error 500
        # The '500 => 1' logic is handled by the base class mock for compatibility
        response = self.request(request, error_code_logging_override={500: 1})

        self._lastresponse = response

        if _wsman_debug:
            print("<====\n", response.as_string(), "<====\n", file=sys.stderr)

        if response.is_success():
            _xml.string(response.content())
            return _xml.dump_as_hash()
        
        # Handle non-successful response that might contain SOAP Fault (HTTP 500)
        content_type = response.header('Content-Type')
        if content_type and 'application/soap+xml' in content_type:
            _xml.string(response.content())
            response_hash = _xml.dump_as_hash()
            envelope = Envelope(response_hash)
            
            # Mock check for fault action
            if envelope.header.action().is("fault"):
                # Mock extraction of error code
                code = envelope.body.fault.get('errorCode') # Need to assume where code is
                if code and code == '2150858752':
                    resource_name = f"{self._resource_class} " if self._resource_class else ""
                    return self.abort(f"WMI {resource_name}resource not available")
                
                self.debug2("Raw client xml request: " + message)
                self.debug2("Raw server xml answer: " + response.content())
                
                # Mock extraction of fault text
                text = envelope.body.fault.get('reason_text')
                return self.abort(text or response.status_line())

        # Final check for failure
        if not response.is_success():
            status = response.status_line()
            return self.abort(status)
        
        return None

    def identify(self) -> Optional[Identify]:
        """Sends a WS-Man Identify request to the service."""
        request = Envelope(
            Namespace('s', 'wsmid'),
            Header(),
            Body(Identify()),
        )

        # Build header for unauthenticated WINRM if necessary
        header_params = {}
        if self._winrm and self._noauth:
            header_params['WSMANIDENTIFY'] = 'unauthenticated'

        response = self._send(request, header_params)
        if not response:
            return None

        envelope = Envelope(response)
        body = envelope.body
        if not isinstance(body, Body):
            return self.abort("Malformed identify response, no 'body' node found")

        # Mock extraction of IdentifyResponse
        identify = body.get("IdentifyResponse") or Identify()
        if not identify.isvalid():
            return self.abort("Malformed identify response, not valid")

        # Mock logger usage
        self.debug2(f"Identify response: {identify.get('ProductVendor')} - {identify.get('ProductVersion')}")

        # Get remote lang as default lang for future exchanges
        lang = envelope.attribute('xml:lang')
        if lang:
            self._lang = lang
            self.debug2(f"Identify response language: {lang}")

        return identify

    def resource_url(self, class_name: str, moniker: Optional[str] = None) -> Optional[str]:
        """Constructs the WS-Man ResourceURI based on class and moniker."""
        path = "cimv2"

        if moniker:
            moniker = moniker.replace('\\', '/')
            match = re.search(r'root/(.*)$', moniker, re.IGNORECASE)
            if not match:
                return self.abort(f"Wrong moniker for request: {moniker}")
            path = match.group(1).rstrip('/')

        return f"http://schemas.microsoft.com/wbem/wsman/1/wmi/root/{path.lower()}/{class_name.lower()}"

    def enumerate(self, **params: Any) -> List[Dict[str, Any]]:
        """Handles WS-Man Enumerate and subsequent Pull operations."""
        items: List[Dict[str, Any]] = []
        
        # Perl's logic: $class = $params{query} ? '*' : $params{class};
        class_name = '*' if params.get('query') else params.get('class')
        
        # Perl's logic: $self->{_resource_class} = $class unless $class eq '*';
        if class_name != '*':
            self._resource_class = class_name
            
        url = self.resource_url(class_name, params.get('moniker'))
        if not url: return []

        messageid = MessageID()
        sid = SessionId()
        operationid = OperationID()
        
        body: Body
        if params.get('query'):
            # Perl's logic: encode('UTF-8',$params{query}) is done by the Filter object
            body = Body(
                Enumerate(
                    OptimizeEnumeration(),
                    MaxElements(32000),
                    Filter(params['query'].encode('utf-8')),
                )
            )
        else:
            body = Body(Enumerate())

        action = Action("enumerate")

        log_msg = f"Requesting enumerate: {params['query']}" if params.get('query') else f"Requesting enumerate URL: {url}"
        self.debug2(log_msg)

        # Determine namespaces for the Envelope (p is likely wsmid in Perl)
        # Perl: Namespace->new($params{selectorset} ? qw(s a w p) : qw(s a n w p b))
        namespaces = ['s', 'a', 'w', 'p'] # simplified mock

        request = Envelope(
            Namespace(*namespaces),
            Header(
                To(self.url()),
                ResourceURI(url),
                ReplyTo().anonymous,
                action,
                messageid,
                MaxEnvelopeSize(512000),
                Locale(self._lang),
                DataLocale(self._lang),
                sid,
                operationid,
                SequenceId(),
                OperationTimeout(60),
                # SelectorSet logic would go here if implemented
            ),
            body,
        )

        while True:
            response_hash = self._send(request)
            if not response_hash:
                break

            envelope = Envelope(response_hash)
            header = envelope.header
            if not isinstance(header, Header):
                self.lasterror("Malformed enumerate response, no 'Header' node found")
                break

            respaction = header.action()
            if not isinstance(respaction, Action):
                self.lasterror("Malformed enumerate response, no 'Action' found in Header")
                break

            ispull = respaction.is('pullresponse')
            if not (ispull or respaction.is('enumerateresponse')):
                self.lasterror(f"Not an enumerate response but {respaction.what()}")
                break

            related = header.get('RelatesTo')
            if not related or related.string() != messageid.string():
                self.lasterror("Got message not related to our enumeration request")
                break

            thisopid = header.get('OperationID')
            if not (thisopid and thisopid.equals(operationid)):
                self.lasterror("Got message not related to our operation")
                break

            respbody = envelope.body
            if not isinstance(respbody, Body):
                self.lasterror("Malformed enumerate response, no 'Body' node found")
                break

            enum = respbody.enumeration(ispull)
            enum_items = enum.items()

            if params.get('method'):
                # Handle methods requested on each enumerated item
                for item in enum_items:
                    if not isinstance(item, dict): continue

                    class_ = item.get('CreationClassName')
                    if not class_: continue

                    selector_prop = params.get('selector')
                    selector_value = item.get(selector_prop)
                    if selector_value is None: continue

                    selectorset = [f"{selector_prop}={selector_value}"]
                    
                    result = self.runmethod(
                        class_=class_,
                        moniker=params.get('moniker'),
                        method=params.get('method'),
                        selectorset=selectorset,
                        params=params.get('params', []),
                        binds=params.get('binds')
                    )
                    
                    if params.get('properties'):
                        items.append(_extract(result, params['properties']))
                    else:
                        items.append(result)
            
            elif params.get('properties'):
                # Extract properties from results
                items.extend([_extract(item, params['properties']) for item in enum_items])
            else:
                # Add all results
                items.extend(enum_items)

            if enum.end_of_sequence():
                break

            # Prepare for next Pull request

            # Fix Envelope namespaces (simplified mock)
            request.reset_namespace("s,a,n,w,p")

            # Update Action to Pull
            action.set("pull")

            # Update MessageID & OperationID
            messageid.reset_uuid()
            operationid.reset_uuid()

            # Reset Body to make Pull request with provided EnumerationContext
            body.reset(Pull(enum.context))

        # Send End to remote (outside the loop, regardless of break reason)
        self.end(operationid)

        # Forget what resource was requested
        del self._resource_class

        return items

    def runmethod(self, **params: Any) -> Optional[Dict[str, Any]]:
        """Executes a WS-Man method (like a WMI method)."""
        if not params.get('method'):
            return self.abort("Not method to set as action")

        url = self.resource_url(params.get('class'), params.get('moniker'))
        if not url: return None

        messageid = MessageID()
        sid = SessionId()
        operationid = OperationID()
        ns = "rm"

        selectorset_elements: List[SelectorSet] = []
        if params.get('selectorset'):
            selectors = [Selector(s) for s in params['selectorset']]
            selectorset_elements.append(SelectorSet(*selectors))

        valueset: List[Node] = []
        what: Optional[str] = None
        
        # Registry path parsing (used for MS-WSMV methods like GetValue/EnumKeys)
        if params.get('path'):
            hKey, keypath, keyvalue = None, None, None
            
            if params['method'].startswith('Enum'):
                match = re.match(r'^(HKEY_[^/]+)/(.*)$', params['path'])
                if match:
                    hKey, keypath = match.groups()
                what = "key values" if params['method'].startswith('EnumValues') else "key subkeys"
            else:
                match = re.match(r'^(HKEY_[^/]+)/(.*)/([^/]+)$', params['path'])
                if match:
                    hKey, keypath, keyvalue = match.groups()
                what = "value"
            
            if not hKey or not keypath:
                return self.abort(f"Unsupported {params['path']} registry path")

            keypath = keypath.replace('/', '\\')
            
            hdefkey = _HIVEREF.get(hKey.upper())
            if hdefkey is None:
                return self.abort(f"Unsupported registry hive in {params['path']} registry path")

            # Prepare ValueSet (Registry method specific nodes)
            valueset.append(Node(Namespace(ns, url), __nodeclass__="hDefKey", content=hdefkey))
            valueset.append(Node(Namespace(ns, url), __nodeclass__="sSubKeyName", content=keypath))
            if keyvalue is not None:
                valueset.append(Node(Namespace(ns, url), __nodeclass__="sValueName", content=keyvalue))
            
            for node in valueset:
                node.reset_namespace()

        method_node = Node(
            Namespace(ns, url),
            __nodeclass__=f"{params['method']}_INPUT",
            content=valueset,
        )
        body = Body(method_node)
        action = Action(f"{url}/{params['method']}")

        if not params.get('nodebug'):
            log_msg = (
                f"Looking for {params['path']} registry {what} via winrm" if what else
                f"Requesting {params['method']} action on resource: {url}"
            )
            self.debug2(log_msg)

        request = Envelope(
            Namespace('s', 'a', 'w', 'p'),
            Header(
                To(self.url()),
                ResourceURI(url),
                ReplyTo().anonymous,
                action,
                messageid,
                MaxEnvelopeSize(512000),
                Locale(self._lang),
                DataLocale(self._lang),
                sid,
                operationid,
                SequenceId(),
                OperationTimeout(60),
                *selectorset_elements,
            ),
            body,
        )

        response_hash = self._send(request)
        if not response_hash:
            return None

        envelope = Envelope(response_hash)

        # Response validation (similar to enumerate/identify)
        header = envelope.header
        if not isinstance(header, Header): return self.abort("Malformed run method response, no 'Header' node found")
        respaction = header.action()
        if not isinstance(respaction, Action): return self.abort("Malformed run method response, no 'Action' found in Header")
        if respaction.what() != f"{url}/{params['method']}Response": return self.abort(f"Not a run method response but {respaction.what()}")
        related = header.get('RelatesTo')
        if not related or related.string() != messageid.string(): return self.abort("Got message not related to our run method request")
        thisopid = header.get('OperationID')
        if not (thisopid and thisopid.equals(operationid)): return self.abort("Got message not related to our run method operation")
        respbody = envelope.body
        if not isinstance(respbody, Body): return self.abort("Malformed run method response, no 'Body' node found")

        # Return method result as a hash (Perl's logic is complex here for handling uValue)
        result: Dict[str, Any] = {}
        node = respbody.get(f"{params['method']}_OUTPUT")
        
        for key in params.get('params', []):
            value: Any = None
            keynode = node.get(key)
            nodes = keynode.nodes() if keynode else []

            # Mocking complex value extraction logic from Perl
            if nodes and key == 'uValue':
                # Perl logic: join('', map { chr($_->string()) } @nodes) -> char array to string
                # Mocking simple join
                value = "".join([n.string() for n in nodes])
            elif nodes and re.match(r'^(sNames|Types)$', key):
                value = [n.string() for n in nodes]
            elif keynode:
                string_val = keynode.string()
                value = [string_val] if re.match(r'^(sNames|Types)$', key) else string_val
            
            # Perl's binding logic
            if params.get('binds') and params['binds'].get(key):
                key = params['binds'][key]
            
            result[key] = value

        # Send End to remote
        self.end(operationid)

        return result

    def shell(self, command: str) -> Optional[Dict[str, Any]]:
        """
        Creates a remote shell, executes a command, retrieves output,
        signals termination, and deletes the shell resource.
        """
        if not command: return None

        # Log command (Perl's logic to limit log size)
        if self.debug():
            logcommand = command
            # Simplified log truncation (Perl regex not perfectly matched)
            if len(logcommand) > 120:
                logcommand = logcommand[:115] + " ..."
            self.debug2(f"Requesting '{logcommand}' run to {self.url()}")

        # --- 1. CREATE SHELL ---
        messageid = MessageID()
        sid = SessionId()
        operationid = OperationID()
        shell = Shell()
        action = Action("create")
        resource = ResourceURI("http://schemas.microsoft.com/wbem/wsman/1/windows/shell/cmd")

        optionset = OptionSet(
            Option('WINRS_NOPROFILE', "TRUE"),
            Option('WINRS_CODEPAGE', "65001"),
        )

        request = Envelope(
            Namespace('s', 'a', 'w', 'p'),
            Header(
                To(self.url()),
                resource,
                ReplyTo().anonymous,
                action,
                messageid,
                MaxEnvelopeSize(512000),
                Locale(self._lang),
                DataLocale(self._lang),
                sid,
                operationid,
                SequenceId(),
                OperationTimeout(60),
                optionset,
            ),
            Body(shell),
        )

        response_hash = self._send(request)
        if not response_hash: return None

        envelope = Envelope(response_hash)

        # Response validation (create)
        header = envelope.header
        if not isinstance(header, Header): return self.abort("Malformed create response, no 'Header' node found")
        respaction = header.action()
        if not isinstance(respaction, Action): return self.abort("Malformed create response, no 'Action' found in Header")
        if not respaction.is('createresponse'): return self.abort(f"Not a create response but {respaction.what()}")
        related = header.get('RelatesTo')
        if not related or related.string() != messageid.string(): return self.abort("Got message not related to our shell create request")
        thisopid = header.get('OperationID')
        if not (thisopid and thisopid.equals(operationid)): return self.abort("Got message not related to our shell create operation")
        respbody = envelope.body
        if not isinstance(respbody, Body): return self.abort("Malformed create response, no 'Body' node found")
        created = respbody.get('ResourceCreated')
        if not isinstance(created, WsManElement): return self.abort("Malformed create response, no 'ResourceCreated' node found")
        reference = created.get('ReferenceParameters')
        if not isinstance(reference, WsManElement): return self.abort("Malformed create response, no 'ReferenceParameters' returned")
        selectorset = reference.get('SelectorSet')
        if not isinstance(selectorset, SelectorSet): return self.abort("Malformed create response, no 'SelectorSet' returned")

        # --- 2. EXECUTE COMMAND ---
        messageid = MessageID()
        operationid = OperationID()
        action = Action("command")
        optionset = OptionSet(Option('WINRS_CONSOLEMODE_STDIN', "TRUE"))

        request = Envelope(
            Namespace('s', 'a', 'w', 'p'),
            Header(
                To(self.url()),
                resource,
                ReplyTo().anonymous,
                action,
                messageid,
                MaxEnvelopeSize(512000),
                Locale(self._lang),
                DataLocale(self._lang),
                sid,
                operationid,
                SequenceId(),
                selectorset,
                OperationTimeout(60),
                optionset,
            ),
            Body(shell.commandline(command)),
        )
        response_hash = self._send(request)
        if not response_hash: return self.abort("No command response")

        envelope = Envelope(response_hash)
        
        # Response validation (command)
        header = envelope.header
        if not isinstance(header, Header): return self.abort("Malformed command response, no 'Header' node found")
        respaction = header.action()
        if not isinstance(respaction, Action): return self.abort("Malformed command response, no 'Action' found in Header")
        if not respaction.is('commandresponse'): return self.abort(f"Not a command response but {respaction.what()}")
        related = header.get('RelatesTo')
        if not related or related.string() != messageid.string(): return self.abort("Got message not related to our shell command request")
        thisopid = header.get('OperationID')
        if not (thisopid and thisopid.equals(operationid)): return self.abort("Got message not related to our shell command operation")
        respbody = envelope.body
        if not isinstance(respbody, Body): return self.abort("Malformed command response, no 'Body' node found")
        respcmd = respbody.get('CommandResponse')
        if not isinstance(respcmd, WsManElement): return self.abort("Malformed command response, no 'CommandResponse' node found")
        commandid = respcmd.get('CommandId')
        if not isinstance(commandid, CommandId): return self.abort("Malformed command response, no 'CommandId' returned")
        cid = commandid.string()
        if not cid: return self.abort("Malformed command response, no CommandId value found")

        # --- 3. RECEIVE OUTPUT STREAM ---
        buffer = self.receive(sid, resource, selectorset, cid)
        exitcode = self._exitcode if self._exitcode is not None else 255
        del self._exitcode

        # --- 4. SIGNAL TERMINATE ---
        self.signal(sid, resource, selectorset, cid, 'terminate')

        # --- 5. DELETE SHELL RESOURCE ---
        delete_opid = self.delete(sid, resource, selectorset)
        if delete_opid is None: self.lasterror("Resource deletion failure")

        # --- 6. END OPERATION ---
        if delete_opid: self.end(delete_opid)

        # Perl returns a scalar ref: \$buffer. Python returns the string directly.
        return {
            'stdout': buffer,
            'exitcode': exitcode,
        }

    def receive(self, sid: SessionId, resource: ResourceURI, selectorset: SelectorSet, cid: str) -> Optional[str]:
        """Receives output stream from an executing shell command."""
        stdout: Optional[str] = ""

        while True:
            messageid = MessageID()
            operationid = OperationID()

            request = Envelope(
                Namespace('s', 'a', 'w', 'p'),
                Header(
                    To(self.url()),
                    resource,
                    ReplyTo().anonymous,
                    Action("receive"),
                    messageid,
                    MaxEnvelopeSize(512000),
                    Locale(self._lang),
                    DataLocale(self._lang),
                    sid,
                    operationid,
                    SequenceId(),
                    OperationTimeout(60),
                    selectorset,
                ),
                Body(Receive(cid)),
            )

            response_hash = self._send(request)
            if not response_hash: break

            envelope = Envelope(response_hash)

            # Response validation (receive)
            header = envelope.header
            if not isinstance(header, Header): self.abort("Malformed receive response, no 'Header' node found"); break
            action = header.action()
            if not isinstance(action, Action): self.abort("Malformed receive response, no 'Action' found in Header"); break
            if not action.is('receiveresponse'): self.abort(f"Not a receive response but {action.what()}"); break
            related = header.get('RelatesTo')
            if not related or related.string() != messageid.string(): self.abort("Got message not related to receive request"); break
            thisopid = header.get('OperationID')
            if not (thisopid and thisopid.equals(operationid)): self.abort("Got message not related to receive operation"); break
            body = envelope.body
            if not isinstance(body, Body): self.lasterror("Malformed receive response, no 'Body' node found"); break
            received = body.get('ReceiveResponse')
            if not isinstance(received, WsManElement): self.lasterror("Malformed receive response, no 'ReceiveResponse' node found"); break
            cmdstate = received.get('CommandState')
            if not isinstance(cmdstate, WsManElement): self.lasterror("Malformed receive response, no 'CommandState' node found"); break
            streams = received.get('Stream')
            if not isinstance(streams, WsManElement): self.lasterror("Malformed receive response, no 'Stream' node found"); break

            # Mock Stream handling (Real GLPI::Agent::SOAP::WsMan::Stream class does this)
            stderr = streams.get('stderr') # Mock extraction
            current_stdout = streams.get('stdout') # Mock extraction

            if current_stdout is not None:
                stdout += current_stdout

            if stderr and len(stderr):
                # Split and log stderr lines
                for line in stderr.split('\n'):
                    self.debug2(f"Command stderr: {line}")

            # Mock exit code and done state
            exitcode = cmdstate.get('ExitCode')
            if exitcode is not None:
                self.debug2(f"Command exited with code: {exitcode}")
                # Mock stream completeness check
                # self.debug2("Command stdout seems truncated") unless streams.stdout_is_full(cid)
                # self.debug2("Command stderr seems truncated") unless streams.stderr_is_full(cid)
                self._exitcode = exitcode

            if cmdstate.get('Done'): # Mock cmdstate->done(cid)
                break

        return stdout

    def signal(self, sid: SessionId, resource: ResourceURI, selectorset: SelectorSet, cid: str, signal: str):
        """Sends a signal (e.g., terminate) to a running shell command."""
        messageid = MessageID()
        operationid = OperationID()

        request = Envelope(
            Namespace('s', 'a', 'w', 'p'),
            Header(
                To(self.url()),
                resource,
                ReplyTo().anonymous,
                Action("signal"),
                messageid,
                MaxEnvelopeSize(512000),
                Locale(self._lang),
                DataLocale(self._lang),
                sid,
                operationid,
                SequenceId(),
                OperationTimeout(60),
                selectorset,
            ),
            Body(
                Signal(
                    Attribute(f"xmlns:{Shell.xmlns()}", Shell.xsd()),
                    Attribute("CommandId", cid),
                    Code.signal(signal),
                ),
            ),
        )

        response_hash = self._send(request)
        if not response_hash: return None

        envelope = Envelope(response_hash)

        # Response validation (signal)
        header = envelope.header
        if not isinstance(header, Header): return self.abort("Malformed signal response, no 'Header' node found")
        respaction = header.action()
        if not isinstance(respaction, Action): return self.abort("Malformed signal response, no 'Action' found in Header")
        if not respaction.is('signalresponse'): return self.abort(f"Not a signal response but {respaction.what()}")
        related = header.get('RelatesTo')
        if not related or related.string() != messageid.string(): return self.abort("Got message not related to signal request")
        thisopid = header.get('OperationID')
        if not (thisopid and thisopid.equals(operationid)): return self.abort("Got message not related to signal operation")

    def delete(self, sid: SessionId, resource: ResourceURI, selectorset: SelectorSet) -> Optional[OperationID]:
        """Deletes a WS-Man resource (e.g., the shell)."""
        messageid = MessageID()
        operationid = OperationID()

        request = Envelope(
            Namespace('s', 'a', 'w', 'p'),
            Header(
                To(self.url()),
                resource,
                ReplyTo().anonymous,
                Action("delete"),
                messageid,
                MaxEnvelopeSize(512000),
                Locale(self._lang),
                DataLocale(self._lang),
                sid,
                operationid,
                SequenceId(),
                OperationTimeout(60),
                selectorset,
            ),
            Body(),
        )

        response_hash = self._send(request)
        if not response_hash: return None

        envelope = Envelope(response_hash)

        # Response validation (delete)
        header = envelope.header
        if not isinstance(header, Header): return self.abort("Malformed delete response, no 'Header' node found")
        respaction = header.action()
        if not isinstance(respaction, Action): return self.abort("Malformed delete response, no 'Action' found in Header")
        if not respaction.is('deleteresponse'): return self.abort(f"Not a delete response but {respaction.what()}")
        related = header.get('RelatesTo')
        if not related or related.string() != messageid.string(): return self.abort("Got message not related to delete request")
        thisopid = header.get('OperationID')
        if not (thisopid and thisopid.equals(operationid)): return self.abort("Got message not related to delete operation")

        return operationid

    def end(self, operationid: OperationID):
        """Sends a final 'End' action for an OperationID."""
        request = Envelope(
            Namespace('s', 'a', 'w', 'p'),
            Header(
                To("http://www.w3.org/2005/08/addressing/anonymous"), # To->anonymous
                ResourceURI("http://schemas.microsoft.com/wbem/wsman/1/wsman/FullDuplex"),
                Action("end"),
                MessageID(),
                operationid,
            ),
            Body(),
        )
        self._send(request)

if __name__ == '__main__':
    # This block provides a minimal example of how the class would be used.
    import sys
    
    # Simple Logger Mock
    class LoggerMock:
        def debug_level(self): return 2
        def debug(self, msg): print(f"[DEBUG] {msg}")
        def debug2(self, msg): print(f"[DEBUG2] {msg}")
        
    wsman_client = WsManClient(
        url="http://localhost:5985/wsman", 
        logger=LoggerMock(),
        winrm=1, # Assume WinRM is active for shell operations
        user="test", # To set _noauth=0
        password="test"
    )

    print("--- Testing Identify (Mocked) ---")
    wsman_client.identify()
    print(f"Last Error: {wsman_client.lasterror()}")
    print("-" * 35)
    
    # Mocking a response for Enumeration to demonstrate the flow
    mock_enum_response_hash = {
        "s:Envelope": {
            "s:Header": {
                "Action": Action("enumerateresponse").string(),
                "RelatesTo": MessageID().string(),
                "OperationID": OperationID().string()
            },
            "s:Body": {
                "EnumerationResponse": {
                    "Items": [{"CreationClassName": "Win32_Thing", "SelectorProp": "Value1"}]
                }
            }
        }
    }
    _xml.dump_as_hash_for_test(mock_enum_response_hash) # Override global mock XML parser output
    
    print("--- Testing Enumerate (Mocked) ---")
    # This will hit a failure because the mock HTTPClient.request always returns 200/empty SOAP
    # and the custom XML parser mock is too simple to correctly parse the response needed for pull logic.
    # The important part is that the method structure and argument parsing are correct.
    
    # To run successfully, we need to mock the full request/response cycle,
    # but the structure of the call is:
    # results = wsman_client.enumerate(class='Win32_Thing', properties=['CreationClassName'])
    # print(f"Enumerate Results (Mocked): {results}")
    # print(f"Last Error: {wsman_client.lasterror()}")
    
    print("--- Testing RunMethod Registry Path Parsing ---")
    # This checks the complex registry path parsing logic in runmethod
    class_ = "StdRegProv"
    method_enum = "EnumKey"
    method_get = "GetStringValue"
    
    # Mock the method to skip actual send for this test
    def mock_send_skip(self, envelope, header=None): return {}

    original_send = wsman_client._send
    wsman_client._send = mock_send_skip # Temporarily replace _send

    # Test EnumKey path parsing
    wsman_client.runmethod(
        class_=class_, 
        method=method_enum, 
        path="HKEY_LOCAL_MACHINE/SOFTWARE/Microsoft"
    )
    print(f"RunMethod Last Error (Enum): {wsman_client.lasterror()}")

    # Test GetValue path parsing
    wsman_client.runmethod(
        class_=class_, 
        method=method_get, 
        path="HKEY_CURRENT_USER/Software/Test/ValueName"
    )
    print(f"RunMethod Last Error (Get): {wsman_client.lasterror()}")

    wsman_client._send = original_send # Restore _send

    print("--- Note ---")
    print("The core class and methods are converted. Full end-to-end functionality requires")
    print("a complete, working implementation of the 'HTTPClient' and 'GLPIAgentXML' classes,")
    print("which are only mocked here for structural compatibility.")
    
    # Reset globals for clean testing/importing
    _xml.reset()
    _xml = None
    
    sys.exit(0)